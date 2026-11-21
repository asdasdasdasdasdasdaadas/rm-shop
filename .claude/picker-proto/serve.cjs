const http = require("http"), fs = require("fs"), path = require("path");
const root = __dirname, types = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".png": "image/png", ".js": "text/javascript" };
http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split("?")[0]) === "/" ? "index.html" : decodeURIComponent(req.url.split("?")[0]));
  if (!p.startsWith(root) || !fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": types[path.extname(p)] || "application/octet-stream", "Cache-Control": "no-store" });
  fs.createReadStream(p).pipe(res);
}).listen(Number(process.env.PORT) || 8765, "127.0.0.1");
