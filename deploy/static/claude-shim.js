// claude.ai-dakı window.claude.use("sample") interfeysinin əvəzi: sorğular /api/sample serverinə gedir,
// "hesabla" aləti isə əvvəlki kimi brauzerdə işləyir.
(() => {
  const status = fetch("/api/status").then((r) => r.json()).catch(() => ({ ready: false }));
  const MEDIA = ["image/jpeg", "image/png", "image/gif", "image/webp"];
  const MAX_ROUNDS = 8;

  function fail(code, text) {
    const e = new Error(code);
    e.code = code;
    if (text) e.text = text;
    return e;
  }

  function imageBlock(file) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve({
        type: "image",
        source: { type: "base64", media_type: MEDIA.includes(file.type) ? file.type : "image/jpeg", data: String(r.result).split(",")[1] },
      });
      r.onerror = () => reject(fail("image_rejected"));
      r.readAsDataURL(file);
    });
  }

  async function turn(body, signal, onDelta) {
    let res;
    try {
      res = await fetch("/api/sample", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal });
    } catch {
      throw fail(signal?.aborted ? "cancelled" : "upstream_error");
    }
    if (!res.ok) {
      let j = {};
      try { j = await res.json(); } catch {}
      throw fail(j.code || "upstream_error");
    }
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "", final = null;
    try {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let i;
        while ((i = buf.indexOf("\n\n")) >= 0) {
          const chunk = buf.slice(0, i);
          buf = buf.slice(i + 2);
          let ev = "message", data = "";
          for (const line of chunk.split("\n")) {
            if (line.startsWith("event: ")) ev = line.slice(7);
            else if (line.startsWith("data: ")) data += line.slice(6);
          }
          const d = data ? JSON.parse(data) : {};
          if (ev === "text") onDelta(d.text);
          else if (ev === "done") final = d;
          else if (ev === "error") throw fail(d.code || "upstream_error");
        }
      }
    } catch (e) {
      if (signal?.aborted) throw fail("cancelled");
      throw e.code ? e : fail("upstream_error");
    }
    if (!final) throw fail(signal?.aborted ? "cancelled" : "upstream_error");
    return final;
  }

  async function sample(prompt, opts = {}) {
    const tools = opts.tools || [];
    const byName = Object.fromEntries(tools.map((t) => [t.name, t]));
    const toolDefs = tools.map((t) => ({ name: t.name, description: t.description, input_schema: t.inputSchema }));
    const content = [];
    for (const f of opts.images || []) content.push(await imageBlock(f));
    content.push({ type: "text", text: prompt });
    const messages = [{ role: "user", content }];

    for (let round = 0; round < MAX_ROUNDS; round++) {
      let text = "";
      const final = await turn(
        { messages, tools: toolDefs, deep: opts.modelTier === "complex" },
        opts.signal,
        (t) => { text += t; opts.onText?.({ text }); },
      );
      const turnText = final.content.filter((b) => b.type === "text").map((b) => b.text).join("");
      if (final.stop_reason === "refusal") throw fail("refused", turnText || undefined);
      if (final.stop_reason === "tool_use") {
        messages.push({ role: "assistant", content: final.content });
        const results = [];
        for (const b of final.content.filter((x) => x.type === "tool_use")) {
          try {
            const t = byName[b.name];
            if (!t) throw new Error(`Naməlum alət: ${b.name}`);
            results.push({ type: "tool_result", tool_use_id: b.id, content: JSON.stringify(await t.execute(b.input || {})) });
          } catch (e) {
            results.push({ type: "tool_result", tool_use_id: b.id, content: String(e?.message || e), is_error: true });
          }
        }
        messages.push({ role: "user", content: results });
        continue;
      }
      if (!turnText.trim()) throw fail("empty_completion");
      return { text: turnText, truncated: final.stop_reason === "max_tokens" };
    }
    throw fail("upstream_error");
  }
  sample.limits = async () => ({ tools: true, images: { mediaTypes: MEDIA } });

  window.claude = {
    use: async (name) => (name === "sample" && (await status).ready ? sample : null),
  };
})();
