'use strict';
(() => {
const recordKey=q=>q.kind+':'+q.id;
function wordingKey(q){let text=q.kind==='keyword'?q.topic:q.prompt;if(q.part==='d')text=text.split(/discuss this statement/i)[0];return q.part+':'+text.normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}_]+/gu,' ').trim();}
function shuffle(rows){const result=rows.slice();for(let i=result.length-1;i>0;i--){const j=crypto.getRandomValues(new Uint32Array(1))[0]%(i+1);[result[i],result[j]]=[result[j],result[i]];}return result;}
function chooseSlots(pools,previous=new Set()){
 const groups=pools.map(pool=>{if(!pool.length)throw new Error('No matching alternatives are available.');const group=new Map();for(const q of shuffle(pool)){const k=wordingKey(q);if(!group.has(k))group.set(k,[]);group.get(k).push(q);}return group;});
 const edges=groups.map(group=>shuffle([...group.keys()]).sort((a,b)=>Number(previous.has(a))-Number(previous.has(b)))),owners=new Map(),assigned=new Map();
 function match(slot,seen,freshOnly){for(const identity of edges[slot]){if(seen.has(identity)||freshOnly&&previous.has(identity))continue;seen.add(identity);if(!owners.has(identity)||match(owners.get(identity),seen,freshOnly)){owners.set(identity,slot);assigned.set(slot,identity);return true;}}return false;}
 for(const freshOnly of [true,false])for(let slot=0;slot<pools.length;slot++)if(!assigned.has(slot))match(slot,new Set(),freshOnly);
 const result=new Array(pools.length).fill(null),records=new Map();for(const [slot,identity] of assigned){const q=groups[slot].get(identity)[0];result[slot]=q;records.set(recordKey(q),slot);}
 function matchRecord(slot,seen){for(const identity of edges[slot])for(const q of groups[slot].get(identity)){const k=recordKey(q);if(seen.has(k))continue;seen.add(k);if(!records.has(k)||matchRecord(records.get(k),seen)){records.set(k,slot);result[slot]=q;return true;}}return false;}
 for(let slot=0;slot<result.length;slot++)if(!result[slot]&&!matchRecord(slot,new Set()))throw new Error('There are not enough different question records for this selection.');
 return result;
}
function target(rows,maximum,value,previous=new Set()){
 const grouped=new Map();for(const q of shuffle(rows)){const identity=wordingKey(q);if(!grouped.has(identity))grouped.set(identity,[]);grouped.get(identity).push(q);}
 function solve(groups){const sums=new Map([[0,[]]]);for(const group of groups){const before=[...sums];for(const q of group){const marks=value(q);for(const [sum,items] of before){if(sum+marks<=maximum&&items.length<60&&!sums.has(sum+marks))sums.set(sum+marks,[...items,q]);}}if(sums.has(maximum))return sums.get(maximum);}return null;}
 const fresh=[...grouped].filter(([identity])=>!previous.has(identity)).map(([,group])=>group);
 return solve(fresh)||solve([...grouped.values()])||solve(shuffle(rows).map(q=>[q]));
}
function repeatCount(items,previous=new Set()){const seen=new Set(previous);let count=0;for(const q of items){const identity=wordingKey(q);if(seen.has(identity))count++;seen.add(identity);}return count;}
window.ReReviSelection=Object.freeze({wordingKey,chooseSlots,target,repeatCount,refs:items=>items.slice(0,60).map(q=>({kind:q.kind,id:String(q.id)}))});
})();
