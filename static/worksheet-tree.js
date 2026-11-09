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
function create({getItems,getBank,onChange,notify,omitExtra,prepareItem}){
 const $=id=>document.getElementById(id),enabled=$('ws-exam-numbering');let groups=[],dragging=null;
 const node=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
 const button=(label,fn,disabled=false)=>{const b=node('button',label);b.type='button';b.disabled=disabled;b.addEventListener('click',fn);return b;};
 const members=id=>getItems().filter(q=>q.layout?.group===id);
 const freeNumber=()=>{for(let n=1;n<=60;n++)if(!groups.some(g=>g.number===n))return n;return null;};
 function unusedPart(group,q){const used=new Set(members(group).filter(n=>n!==q).map(n=>n.layout?.part));if(!used.has(q.part))return q.part;for(let n=1;n<=60;n++){const label=q.part+'('+roman(n)+')';if(!used.has(label))return label;}}
 function normalise(){
  if(!enabled.checked)return;
  const items=getItems();
  for(const q of items){
   let group=groups.find(g=>g.id===q.layout?.group);
   if(!group&&groups.length>=60)group=groups.find(g=>!members(g.id).length)||groups[0];
   if(!group&&validLayout(q.layout)){
    const l=q.layout;group={id:l.group,number:groups.some(g=>g.number===l.number)?freeNumber():l.number,title:l.title.trim()};groups.push(group);
   }
   if(!group){
    const id=('topic-'+q.component+'-'+q.number).slice(0,100);group=groups.find(g=>g.id===id);
    if(!group){const proposed=Number(q.number);group={id,number:Number.isInteger(proposed)&&proposed>=1&&proposed<=60&&!groups.some(g=>g.number===proposed)?proposed:freeNumber(),title:(q.section_topic||q.topic||'Questions').slice(0,120)};groups.push(group);}
   }
   const part=validLayout(q.layout)&&q.layout.group===group.id?q.layout.part:unusedPart(group.id,q);
   q.layout={group:group.id,number:group.number,title:group.title,part};
  }
  // Stable grouping preserves the order of subquestions and all work stays keyed to question IDs.
  const order=new Map(groups.map((g,i)=>[g.id,i]));items.sort((a,b)=>order.get(a.layout.group)-order.get(b.layout.group));
 }
 function commit(text){normalise();onChange();if(text)notify(text);}
 function moveQuestion(q,target,before=null){
  const group=groups.find(g=>g.id===target);if(!q||!group)return;
  const items=getItems(),index=items.indexOf(q),oldGroup=q.layout?.group;
  if(index>=0)items.splice(index,1);else if(items.length>=60){notify('A worksheet can contain at most 60 questions.');return;}
  const oldPart=q.layout?.part;const label=oldGroup===target||oldPart&&validPart.test(oldPart)&&!members(target).some(n=>n.layout?.part===oldPart)?oldPart:unusedPart(target,q);
  q.layout={group:target,number:group.number,title:group.title,part:label};
  let at=before?items.findIndex(n=>identity(n)===before):-1;
  if(at<0){const last=items.findLastIndex(n=>n.layout?.group===target);at=last<0?items.length:last+1;}
  items.splice(at,0,q);commit('Moved '+q.layout.number+'('+q.layout.part+') · '+q.topic+'. Answers and marks were kept.');
 }
 function moveGroup(id,direction){const at=groups.findIndex(g=>g.id===id),to=at+direction;if(at<0||to<0||to>=groups.length)return;[groups[at],groups[to]]=[groups[to],groups[at]];commit('Main question moved. Its display number is unchanged; you can edit it or renumber the tree.');}
 function canMove(q,delta){const list=members(q.layout?.group),index=list.indexOf(q);return index+delta>=0&&index+delta<list.length;}
 function moveWithin(q,delta){const list=members(q.layout?.group),other=list[list.indexOf(q)+delta];if(!other)return;const items=getItems(),a=items.indexOf(q),b=items.indexOf(other);[items[a],items[b]]=[items[b],items[a]];commit();}
 function grip(payload,label){const n=button('↕',()=>notify('Drag this handle, or use the move buttons and group menu.'));n.className='ws-drag-handle';n.draggable=true;n.setAttribute('aria-label',label);n.title=label;n.addEventListener('dragstart',event=>{dragging=payload;event.dataTransfer.setData(type,JSON.stringify(payload));event.dataTransfer.effectAllowed=payload.kind==='bank'?'copyMove':'move';event.stopPropagation();});n.addEventListener('dragend',()=>{dragging=null;document.querySelectorAll('.ws-drop-over').forEach(n=>n.classList.remove('ws-drop-over'));});return n;}
 function dropzone(n,group,before=null){
  n.addEventListener('dragover',event=>{if(event.dataTransfer.types.includes(type)){event.preventDefault();event.stopPropagation();n.classList.add('ws-drop-over');}});
  n.addEventListener('dragleave',()=>n.classList.remove('ws-drop-over'));
  n.addEventListener('drop',event=>{
   if(!event.dataTransfer.types.includes(type))return;event.preventDefault();event.stopPropagation();n.classList.remove('ws-drop-over');
   let data;try{data=JSON.parse(event.dataTransfer.getData(type));}catch{return;}dragging=null;
   if(data.kind==='group'){const from=groups.findIndex(g=>g.id===data.id),to=groups.findIndex(g=>g.id===group);if(from<0||to<0||from===to)return;const [g]=groups.splice(from,1);groups.splice(groups.findIndex(g=>g.id===group),0,g);commit('Main question group moved.');return;}
   let q=getItems().find(q=>identity(q)===data.key);
   if(!q&&data.kind==='bank'){
    const source=getBank().find(q=>identity(q)===data.key);if(!source||omitExtra()&&source.source_type==='additional'){notify('That question is excluded by the current source setting.');return;}
    q=prepareItem(source);
   }
   if(q&&identity(q)!==before)moveQuestion(q,group,before);
  });
 }
 function render(){
  normalise();$('ws-tree-body').hidden=!enabled.checked;
  const container=$('ws-question-tree');container.replaceChildren();if(!enabled.checked)return;
  groups.forEach((group,index)=>{
   const section=node('section',undefined,'ws-tree-group');section.dataset.group=group.id;dropzone(section,group.id);
   const heading=node('div',undefined,'ws-tree-heading');heading.append(grip({kind:'group',id:group.id},'Drag main question '+group.number));
   const numberLabel=node('label','Question number'),number=node('input');number.type='number';number.min=1;number.max=60;number.value=group.number;number.setAttribute('aria-label','Main question number for '+group.title);numberLabel.append(number);
   number.addEventListener('change',()=>{const value=Number(number.value);if(!Number.isInteger(value)||value<1||value>60||groups.some(g=>g!==group&&g.number===value)){number.value=group.number;notify('Use an unused whole question number from 1 to 60.');return;}group.number=value;commit();});
   const titleLabel=node('label','Topic / heading'),title=node('input');title.maxLength=120;title.value=group.title;title.setAttribute('aria-label','Heading for question '+group.number);titleLabel.append(title);title.addEventListener('change',()=>{if(!title.value.trim()){title.value=group.title;notify('The heading cannot be empty.');return;}group.title=title.value.trim();commit();});
   heading.append(numberLabel,titleLabel,button('Group up',()=>moveGroup(group.id,-1),index===0),button('Group down',()=>moveGroup(group.id,1),index===groups.length-1));
   const list=members(group.id);if(!list.length)heading.append(button('Remove empty group',()=>{groups=groups.filter(g=>g!==group);commit();}));section.append(heading);
   const children=node('ol',undefined,'ws-tree-children');
   list.forEach((q,i)=>{
    const row=node('li',undefined,'ws-tree-question');row.dataset.key=identity(q);dropzone(row,group.id,identity(q));
    const partLabel=node('label','Subquestion'),part=node('input');part.value=q.layout.part;part.maxLength=11;part.setAttribute('aria-label','Subquestion label for '+q.topic);partLabel.append(part);
    part.addEventListener('change',()=>{const value=part.value.trim().toLowerCase().replace(/^\(([a-z])\)/,'$1');if(!validPart.test(value)||members(group.id).some(n=>n!==q&&n.layout.part===value)){part.value=q.layout.part;notify('Use a unique label such as a, b or b(ii) within this group.');return;}q.layout.part=value;commit();});
    const text=node('div',undefined,'ws-tree-question-text');text.append(node('strong',q.part.toUpperCase()+') '+(q.section_topic||q.topic)+' · '+q.marks+' marks'+(q.spag?' + 6 SPaG':'')),node('p',q.prompt.length>160?q.prompt.slice(0,160)+'…':q.prompt));
    const destination=node('select');destination.setAttribute('aria-label','Move '+q.layout.number+'('+q.layout.part+') to main question');groups.forEach(g=>destination.add(new Option(g.number+'. '+g.title,g.id)));destination.value=group.id;destination.addEventListener('change',()=>moveQuestion(q,destination.value));
    row.append(grip({kind:'selected',key:identity(q)},'Drag '+q.layout.number+'('+q.layout.part+') '+q.topic),partLabel,text,button('Up',()=>moveWithin(q,-1),i===0),button('Down',()=>moveWithin(q,1),i===list.length-1),destination);children.append(row);
   });
   if(!list.length)children.append(node('li','Drop questions from the bank or another group here.','ws-tree-empty'));
   section.append(children);container.append(section);
  });
  if(!groups.length)container.append(node('p','Add questions from the bank, or create a main question group and drag questions into it.'));
 }
 enabled.addEventListener('change',()=>commit());
 $('ws-tree-add-group').addEventListener('click',()=>{if(groups.length>=60){notify('You can have at most 60 main question groups.');return;}groups.push({id:'custom-'+crypto.randomUUID(),number:freeNumber(),title:'New main question'});commit();});
 $('ws-tree-renumber').addEventListener('click',()=>{groups.forEach((g,i)=>g.number=i+1);commit('Main questions renumbered in their current order. Subquestion labels were kept.');});
 $('ws-tree-regroup').addEventListener('click',()=>{groups=[];getItems().forEach(q=>delete q.layout);enabled.checked=true;commit('Question tree reset from original topics.');});
 return {
  render,normalise,canMove,moveWithin,isEnabled:()=>enabled.checked,
  label:(q,index)=>enabled.checked&&q.layout?String(q.layout.number)+'('+q.layout.part[0]+')'+q.layout.part.slice(1):String(index+1)+' ('+q.part+')',
  bankHandle:q=>grip({kind:'bank',key:identity(q)},'Drag '+q.part.toUpperCase()+') '+(q.section_topic||q.topic)+' into a main question group'),
  state:()=>({enabled:enabled.checked,groups:structuredClone(groups)}),
  reset:(active=enabled.checked)=>{groups=[];enabled.checked=active;},
  restore:state=>{groups=[];enabled.checked=state?.enabled===true;const seen=new Set(),numbers=new Set();if(Array.isArray(state?.groups))for(const g of state.groups.slice(0,60)){if(g&&typeof g.id==='string'&&validGroup.test(g.id)&&Number.isInteger(g.number)&&g.number>0&&g.number<=60&&typeof g.title==='string'&&g.title.trim()&&g.title.length<=120&&!seen.has(g.id)&&!numbers.has(g.number)){groups.push({id:g.id,number:g.number,title:g.title.trim()});seen.add(g.id);numbers.add(g.number);}}}
 };
}
window.ReReviTree=Object.freeze({create,validatePaper});
})();
