const assert=require('node:assert/strict');
(async()=>{
 const {requiredUsers}=await import('../src/lib/finance-calculator.mjs');
 const base={target:100000,arpu:180,fee:0,fixed:0,variable:0,profit:false};
 assert.equal(requiredUsers(base).users,556);
 assert.equal(requiredUsers({...base,target:0}).users,0);
 assert.equal(requiredUsers({...base,profit:true,fee:10,fixed:10000,variable:62}).users,1100);
 assert.equal(requiredUsers({...base,profit:true,fee:100}),null);
 assert.equal(requiredUsers({...base,arpu:0}),null);
 assert.equal(requiredUsers({...base,target:NaN}),null);
 assert.equal(requiredUsers({...base,profit:true,variable:200}),null);
 console.log('Finance calculator: 7 checks passed');
})();
