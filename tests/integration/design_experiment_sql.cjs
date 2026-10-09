// Run with PGLITE_MODULE pointing to @electric-sql/pglite (PostgreSQL WASM).
const {PGlite}=require(process.env.PGLITE_MODULE || '@electric-sql/pglite');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const db=new PGlite();
 try {
  const root=path.resolve(__dirname,'../..');
  await db.exec(fs.readFileSync(path.join(root,'app/schema.sql'),'utf8'));
  const source=fs.readFileSync(path.join(root,'app/design_experiment.py'),'utf8');
  const sql=[...source.matchAll(/'''([\s\S]*?)'''/g)].map(m=>m[1]);
  const [assign,expose,event,stats]=sql;
  const key='cabinet_dark_v2';
  await db.exec(`INSERT INTO users(telegram_id) VALUES(1),(2),(3),(4);`);
  for(const id of [1,2,3,4]) await db.query(assign,[key,id,id===4?'classic':'modern']);
  const stored=await db.query(assign,[key,1,'classic']);assert.equal(stored.rows[0].variant,'modern');
  await db.query(expose,[key,1,'classic']);
  assert.equal((await db.query('SELECT exposed_at FROM design_exposures WHERE telegram_id=1')).rows[0].exposed_at,null);
  await db.query(event,[key,1,'topup','modern']);
  assert.equal((await db.query('SELECT * FROM design_events')).rows.length,0);
  for(const id of [1,2,3,4]) await db.query(expose,[key,id,id===4?'classic':'modern']);
  await db.exec(`UPDATE design_exposures SET exposed_at=NOW()-INTERVAL '8 days' WHERE telegram_id<>3;
    UPDATE users SET first_online_at=NOW()-INTERVAL '7 days' WHERE telegram_id=1;
    INSERT INTO payments(telegram_id,plan_code,stars,created_at) VALUES(1,'topup_100',100,NOW()-INTERVAL '7 days'),(1,'topup_100',100,NOW()-INTERVAL '6 days'),(2,'topup_100',100,NOW()),(3,'topup_100',100,NOW());`);
  await db.query(event,[key,3,'topup','modern']);await db.query(event,[key,3,'topup','modern']);
  assert.equal((await db.query('SELECT * FROM design_events')).rows.length,1);
  const result=(await db.query(stats,[key])).rows;
  const modern=result.find(r=>r.variant==='modern');
  assert.equal(modern.exposed,3);assert.equal(modern.mature,2);assert.equal(modern.paid,1);assert.equal(modern.connected,1);assert.equal(modern.connection_base,2);
  assert.equal(result.find(r=>r.variant==='classic').paid,0);
  await db.exec(`INSERT INTO rollypay_orders(order_id,telegram_id,plan_code,status,paid_at) VALUES('unpaid',4,'topup_300','created',NOW()-INTERVAL '7 days');`);
  assert.equal((await db.query(stats,[key])).rows.find(r=>r.variant==='classic').paid,0);
  await db.exec(`UPDATE rollypay_orders SET status='granted' WHERE order_id='unpaid'`);
  assert.equal((await db.query(stats,[key])).rows.find(r=>r.variant==='classic').paid,1);
  await db.exec(`DELETE FROM rollypay_orders WHERE telegram_id=4`);
  await db.exec('DELETE FROM users WHERE telegram_id=4');
  assert.equal((await db.query('SELECT * FROM design_exposures WHERE telegram_id=4')).rows.length,0);
  console.log('PostgreSQL schema, stable assignment, exposure validation, deduplication, mature cohorts and payment window passed.');
 } finally {await db.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
