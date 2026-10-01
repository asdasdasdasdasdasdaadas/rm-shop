// Optional PostgreSQL-WASM integration harness. No production service/network access.
import {createInterface} from 'node:readline';
import {pathToFileURL} from 'node:url';
const {PGlite} = await import(pathToFileURL(process.env.PGLITE_MODULE));
const db = new PGlite();
for await (const line of createInterface({input: process.stdin})) {
  try {
    const {sql, args, script} = JSON.parse(line);
    const result = script ? await db.exec(sql) : await db.query(sql, args || []);
    process.stdout.write(JSON.stringify({rows: result.rows || []}) + '\n');
  } catch (error) {
    process.stdout.write(JSON.stringify({error: error.message}) + '\n');
  }
}
await db.close();
