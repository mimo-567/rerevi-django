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
function create({getItems,getBank,onChange,notify,omitExtra,prepareItem,removeItem}){
 const $=id=>document.getElementById(id),enabled=$('ws-exam-numbering');let groups=[],dragging=null,paletteRows=[],palettePart='all';
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
 function wireDrag(n,payload){n.draggable=true;n.addEventListener('dragstart',event=>{dragging=payload;event.dataTransfer.setData(type,JSON.stringify(payload));event.dataTransfer.effectAllowed=['bank','new-group'].includes(payload.kind)?'copyMove':'move';event.stopPropagation();});n.addEventListener('dragend',()=>{dragging=null;document.querySelectorAll('.ws-drop-over').forEach(n=>n.classList.remove('ws-drop-over'));});}
 function grip(payload,label){const n=button('↕',()=>notify('Drag this handle, or use the move buttons and group menu.'));n.className='ws-drag-handle';n.setAttribute('aria-label',label);n.title=label;wireDrag(n,payload);return n;}
 function addGroup(before=null){
  if(groups.length>=60){notify('You can have at most 60 main question containers.');return;}
  enabled.checked=true;const group={id:'custom-'+crypto.randomUUID(),number:freeNumber(),title:'New main question'};
  const index=groups.findIndex(g=>g.id===before);if(index<0)groups.push(group);else groups.splice(index,0,group);
  commit('Numbered container added. Edit its heading, then place question blocks inside.');
 }
 function addBankQuestion(key,target){
  const source=getBank().find(q=>identity(q)===key);if(!source||omitExtra()&&source.source_type==='additional'){notify('That question is excluded by the current source setting.');return;}
  if(!target){notify('Add a numbered container first, then choose it as the destination.');return;}
  moveQuestion(getItems().find(q=>identity(q)===key)||prepareItem(source),target);
 }
 function dropzone(n,group,before=null){
  n.addEventListener('dragover',event=>{if(event.dataTransfer.types.includes(type)){event.preventDefault();event.stopPropagation();n.classList.add('ws-drop-over');}});
  n.addEventListener('dragleave',()=>n.classList.remove('ws-drop-over'));
  n.addEventListener('drop',event=>{
   if(!event.dataTransfer.types.includes(type))return;event.preventDefault();event.stopPropagation();n.classList.remove('ws-drop-over');
   let data;try{data=JSON.parse(event.dataTransfer.getData(type));}catch{return;}dragging=null;
   if(data.kind==='new-group'){addGroup(group);return;}
   if(data.kind==='group'){const from=groups.findIndex(g=>g.id===data.id),to=group===null?groups.length:groups.findIndex(g=>g.id===group);if(from<0||to<0||from===to)return;const [g]=groups.splice(from,1);if(group===null)groups.push(g);else groups.splice(groups.findIndex(g=>g.id===group),0,g);commit('Numbered container moved with all its question blocks.');return;}
   if(group===null){notify('Drop question blocks inside a numbered container.');return;}
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
   const section=node('section',undefined,'ws-tree-group');section.dataset.group=group.id;section.setAttribute('aria-label','Question '+group.number+' container: '+group.title);dropzone(section,group.id);
   const heading=node('div',undefined,'ws-tree-heading');heading.append(grip({kind:'group',id:group.id},'Drag main question '+group.number));
   const numberLabel=node('label','Question'),number=node('input');number.type='number';number.min=1;number.max=60;number.value=group.number;number.setAttribute('aria-label','Main question number for '+group.title);numberLabel.append(number);
   number.addEventListener('change',()=>{const value=Number(number.value);if(!Number.isInteger(value)||value<1||value>60||groups.some(g=>g!==group&&g.number===value)){number.value=group.number;notify('Use an unused whole question number from 1 to 60.');return;}group.number=value;commit();});
   const titleLabel=node('label','Container heading'),title=node('input');title.maxLength=120;title.value=group.title;title.setAttribute('aria-label','Heading for question '+group.number);titleLabel.append(title);title.addEventListener('change',()=>{if(!title.value.trim()){title.value=group.title;notify('The heading cannot be empty.');return;}group.title=title.value.trim();commit();});
   heading.append(numberLabel,titleLabel,button('Group up',()=>moveGroup(group.id,-1),index===0),button('Group down',()=>moveGroup(group.id,1),index===groups.length-1));
   const list=members(group.id);if(!list.length)heading.append(button('Remove empty group',()=>{groups=groups.filter(g=>g!==group);commit();}));section.append(heading);
   const children=node('ol',undefined,'ws-tree-children');
   list.forEach((q,i)=>{
    const row=node('li',undefined,'ws-tree-question ws-command-block');row.dataset.part=q.part;row.dataset.key=identity(q);dropzone(row,group.id,identity(q));
    const partLabel=node('label','Subquestion'),part=node('input');part.value=q.layout.part;part.maxLength=11;part.setAttribute('aria-label','Subquestion label for '+q.topic);partLabel.append(part);
    part.addEventListener('change',()=>{const value=part.value.trim().toLowerCase().replace(/^\(([a-z])\)/,'$1');if(!validPart.test(value)||members(group.id).some(n=>n!==q&&n.layout.part===value)){part.value=q.layout.part;notify('Use a unique label such as a, b or b(ii) within this group.');return;}q.layout.part=value;commit();});
    const text=node('div',undefined,'ws-tree-question-text');text.append(node('strong',q.part.toUpperCase()+') '+(q.section_topic||q.topic)),node('span',q.marks+' marks'+(q.spag?' + 6 SPaG':''),'ws-block-marks'),node('p',q.prompt.length>160?q.prompt.slice(0,160)+'…':q.prompt));
    const destination=node('select');destination.setAttribute('aria-label','Move '+q.layout.number+'('+q.layout.part+') to main question');groups.forEach(g=>destination.add(new Option(g.number+'. '+g.title,g.id)));destination.value=group.id;destination.addEventListener('change',()=>moveQuestion(q,destination.value));
    const controls=node('details',undefined,'ws-block-controls');controls.append(node('summary','Block controls'),partLabel,button('Up',()=>moveWithin(q,-1),i===0),button('Down',()=>moveWithin(q,1),i===list.length-1),destination,button('Remove block',()=>removeItem(q)));
    row.append(grip({kind:'selected',key:identity(q)},'Drag '+q.layout.number+'('+q.layout.part+') '+q.topic),node('span','('+q.layout.part[0]+')'+q.layout.part.slice(1),'ws-block-label'),text,controls);children.append(row);
   });
   children.append(node('li',list.length?'Drop a question here to add it at the end.':'Drop question blocks inside this numbered container.','ws-tree-empty'));
   section.append(children);container.append(section);
  });
  container.append(node('p',groups.length?'Drop a question number container here to add another main question.':'Your paper starts here. Drag a question number container from the palette, or use Add numbered container.','ws-canvas-empty'));
 }
 enabled.addEventListener('change',()=>commit());
 $('ws-tree-add-group').addEventListener('click',()=>addGroup());
 $('ws-new-group-block').addEventListener('click',()=>addGroup());wireDrag($('ws-new-group-block'),{kind:'new-group'});dropzone($('ws-question-tree'),null);
 $('ws-tree-renumber').addEventListener('click',()=>{groups.forEach((g,i)=>g.number=i+1);commit('Main questions renumbered in their current order. Subquestion labels were kept.');});
 $('ws-tree-regroup').addEventListener('click',()=>{groups=[];getItems().forEach(q=>delete q.layout);enabled.checked=true;commit('Question tree reset from original topics.');});
 function renderPalette(rows=paletteRows){
  paletteRows=rows;const destination=$('ws-palette-target'),old=destination.value;
  destination.replaceChildren(...(groups.length?groups.map(g=>new Option(g.number+'. '+g.title,g.id)):[new Option('Add a numbered container first','')]));
  if(groups.some(g=>g.id===old))destination.value=old;
  const query=$('ws-palette-search').value.trim().toLowerCase();
  const matching=rows.filter(q=>(palettePart==='all'||q.part===palettePart)&&(!query||query.split(/\s+/).every(term=>[q.topic,q.section_topic,q.prompt,q.component].join(' ').toLowerCase().includes(term))));
  $('ws-palette-count').textContent=matching.length+' matching question blocks'+(matching.length>60?' · showing the first 60; refine the search for more.':'.');
  const container=$('ws-question-palette');container.replaceChildren();
  for(const q of matching.slice(0,60)){
   const block=node('article',undefined,'ws-palette-block ws-command-block');block.dataset.part=q.part;block.dataset.key=identity(q);
   const handle=grip({kind:'bank',key:identity(q)},'Drag '+q.part.toUpperCase()+') '+(q.section_topic||q.topic)+' into a numbered container');
   const body=node('div',undefined,'ws-palette-block-text');body.append(node('strong',q.part.toUpperCase()+') '+(q.section_topic||q.topic)),node('span',q.marks+' marks · '+({'component-1-general':'Component 1','component-2-christianity':'Christianity','component-3-islam':'Islam'}[q.component]||q.component),'ws-block-marks'));
   const detail=node('details');detail.append(node('summary','Read question'),node('p',q.prompt),node('p','Source: '+q.source_label));
   const present=getItems().some(n=>identity(n)===identity(q));const add=button(present?'Move here':'Add',()=>addBankQuestion(identity(q),destination.value),!groups.length||!present&&getItems().length>=60);add.setAttribute('aria-label',(present?'Move ':'Add ')+q.part.toUpperCase()+') '+(q.section_topic||q.topic)+' to chosen container');
   block.append(handle,body,add,detail);container.append(block);
  }
  if(!matching.length)container.append(node('p','No matching blocks. Change the search or the filters in section 2.'));
 }
 $('ws-palette-search').addEventListener('input',()=>renderPalette());
 $('ws-palette-parts').querySelectorAll('[data-palette-part]').forEach(button=>button.addEventListener('click',()=>{palettePart=button.dataset.palettePart;$('ws-palette-parts').querySelectorAll('[data-palette-part]').forEach(n=>n.setAttribute('aria-pressed',String(n===button)));renderPalette();}));
 return {
  render,renderPalette,normalise,canMove,moveWithin,isEnabled:()=>enabled.checked,
  label:(q,index)=>enabled.checked&&q.layout?String(q.layout.number)+'('+q.layout.part[0]+')'+q.layout.part.slice(1):String(index+1)+' ('+q.part+')',
  bankHandle:q=>grip({kind:'bank',key:identity(q)},'Drag '+q.part.toUpperCase()+') '+(q.section_topic||q.topic)+' into a main question group'),
  state:()=>({enabled:enabled.checked,groups:structuredClone(groups)}),
  reset:(active=enabled.checked)=>{groups=[];enabled.checked=active;},
  restore:state=>{groups=[];enabled.checked=state?.enabled===true;const seen=new Set(),numbers=new Set();if(Array.isArray(state?.groups))for(const g of state.groups.slice(0,60)){if(g&&typeof g.id==='string'&&validGroup.test(g.id)&&Number.isInteger(g.number)&&g.number>0&&g.number<=60&&typeof g.title==='string'&&g.title.trim()&&g.title.length<=120&&!seen.has(g.id)&&!numbers.has(g.number)){groups.push({id:g.id,number:g.number,title:g.title.trim()});seen.add(g.id);numbers.add(g.number);}}}
 };
}
window.ReReviTree=Object.freeze({create,validatePaper});
})();
