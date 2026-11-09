'use strict';
(() => {
const type='application/x-rerevi-question';
const identity=q=>q.kind+':'+q.id;
const validPart=/^[a-z](?:\([ivxlcdm]{1,8}\))?$/;
const validGroup=/^[A-Za-z0-9:_-]{1,100}$/;
function roman(n){let result='';for(const [value,letter] of [[50,'l'],[40,'xl'],[10,'x'],[9,'ix'],[5,'v'],[4,'iv'],[1,'i']])while(n>=value){result+=letter;n-=value;}return result;}
function validLayout(l){return l&&typeof l==='object'&&typeof l.group==='string'&&validGroup.test(l.group)&&Number.isInteger(l.number)&&l.number>=1&&l.number<=60&&typeof l.title==='string'&&l.title.trim()&&l.title.length<=120&&typeof l.part==='string'&&validPart.test(l.part);}
function validatePaper(paper){
 if(paper.numbering!==undefined&&!['exam','sequential'].includes(paper.numbering))throw Error('Invalid question numbering mode.');
 const groups=new Map(),numbers=new Map(),labels=new Set(),closed=new Set();let previous=null;
 for(const q of paper.questions){
  if(q.layout!==undefined&&!validLayout(q.layout))throw Error('Invalid question-tree numbering.');
  if(paper.numbering!=='exam')continue;
  const l=q.layout;if(!validLayout(l))throw Error('Every exam-style question needs a valid tree entry.');
  const header=JSON.stringify([l.number,l.title.trim()]);
  if(groups.has(l.group)&&groups.get(l.group)!==header||numbers.has(l.number)&&numbers.get(l.number)!==l.group)throw Error('Main question numbers and headings must be consistent and unique.');
  if(previous!==null&&previous!==l.group)closed.add(previous);
  if(closed.has(l.group)||labels.has(l.group+':'+l.part))throw Error('Keep each group together and use a different label for each subquestion.');
  groups.set(l.group,header);numbers.set(l.number,l.group);labels.add(l.group+':'+l.part);previous=l.group;
 }
}
window.ReReviNumbering=Object.freeze({validatePaper,label:(q,index,mode)=>mode==='exam'&&q.layout?String(q.layout.number)+'('+q.layout.part[0]+')'+q.layout.part.slice(1):String(index+1)+' ('+q.part+')'});
})();
