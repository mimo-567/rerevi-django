'use strict';
(() => {
const $ = id => document.getElementById(id);
const catalogue=JSON.parse($('catalogue-data').textContent);
const examinerReports=JSON.parse($('examiner-report-data').textContent).sort((a,b)=>b.year-a.year);
const form=$('builder-form');
const csrf=form.querySelector('[name=csrfmiddlewaretoken]').value;
const STORAGE='rerevi-practice-v1';
let mode='keywords',paper=null,answers={},marks={},spagMarks={},shared=null,shareBusy=false,timer=null,storageWarned=false,pendingBuild=false;
const el=(tag,className,text)=>{const n=document.createElement(tag);if(className)n.className=className;if(text!==undefined)n.textContent=text;return n;};
const key=q=>q.kind+':'+q.id;
function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(timer);timer=setTimeout(()=>$('toast').hidden=true,5000);}
function persist(){try{sessionStorage.setItem(STORAGE,JSON.stringify({version:1,paper,answers,marks,spagMarks,shared}));}catch(error){if(!storageWarned){toast('Browser storage is unavailable. Save your answers before leaving this page.');storageWarned=true;}}}
function updateOptions(){
 const c=catalogue.find(c=>c.id===$('component').value);
 const oldSection=$('section').value;
 $('section').replaceChildren(new Option('All topics / sections','all'),...c.sections.map(s=>new Option(s[1],s[0])));
 if([...$('section').options].some(o=>o.value===oldSection))$('section').value=oldSection;
 const oldYear=$('year').value;
 $('year').replaceChildren(new Option('Any year','all'),...c.years.map(y=>new Option(y,y)));
 if([...$('year').options].some(o=>o.value===oldYear))$('year').value=oldYear;
 $('section-field').hidden=mode==='full';$('count-field').hidden=mode==='full';$('count').required=mode!=='full';
 $('year-field').hidden=mode==='keywords';$('parts-field').hidden=mode!=='custom';
 $('extra-field').hidden=mode==='keywords';
 const selectedYear=$('year').value!=='all';$('include-extra').disabled=selectedYear;
 $('extra-note').textContent=selectedYear?'A selected year always uses that original past paper. Extra questions are excluded.':'Untick to use official past-paper B, C and D questions only. Extra practice may have no question-specific mark scheme.';
 $('spag-field').hidden=mode==='keywords'||c.id==='component-3-islam';
 if($('spag-field').hidden)$('spag').checked=false;
 $('count-label').textContent=mode==='keywords'?'Number of keywords':'Number of questions';$('count').max=mode==='keywords'?51:30;
 $('preview-title').textContent={keywords:'Key concepts',custom:'Focused practice',full:'A full practice paper'}[mode];
 $('preview-component').textContent=c.name;
 $('preview-count').textContent=mode==='full'?`${c.minutes/60} hour${c.minutes===120?'s':''} · ${c.id==='component-1-general'?120:60} marks`:`${$('count').value} ${mode==='keywords'?'keywords':'questions'}`;
 $('selection-note').textContent=mode==='keywords'?'Different terms each time. No repeats in your set.':mode==='full'?($('year').value==='all'?'A, B, C and D in every section. Part A uses the official glossary.':'Original A, B, C and D questions from the selected past-paper year.'):'Select B, C or D. Additional practice is clearly labelled; self-marking is optional when no indicative content is supplied.';
}
document.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>{
 mode=button.dataset.mode;document.querySelectorAll('[data-mode]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});
 $('count').value=mode==='keywords'?8:6;updateOptions();
}));$('component').addEventListener('change',updateOptions);$('year').addEventListener('change',updateOptions);$('count').addEventListener('input',updateOptions);
function hasWork(){return Object.values(answers).some(a=>a.trim())||Object.keys(marks).length>0;}
form.addEventListener('submit',async event=>{event.preventDefault();if(paper&&hasWork()){pendingBuild=true;$('replace-dialog').showModal();return;}await build();});
async function build(){
 if(shareBusy){toast('Wait for the sharing request to finish before starting a new practice.');return;}
 const button=form.querySelector('[type=submit]');button.disabled=true;button.firstElementChild.textContent='Building your practice…';$('builder-error').hidden=true;
 try{
  const response=await fetch('/api/generate/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify({mode,component:$('component').value,section:$('section').value,count:$('count').value,year:$('year').value,parts:[...form.querySelectorAll('[name=parts]:checked')].map(i=>i.value),spag:$('spag').checked,include_extra:$('include-extra').checked})});
  let data;try{data=await response.json();}catch{throw new Error('The server could not complete that request. Please try again.');}
  if(!response.ok)throw new Error(data.error||'Could not create the paper.');
  paper=data;answers={};marks={};spagMarks={};shared=null;$('share-opt-in').checked=false;$('email-share').checked=false;$('share-status').textContent='';persist();render();updateShare();$('paper-section').scrollIntoView({behavior:'smooth',block:'start'});toast('Your practice is ready. Take it at your own pace.');
 }catch(error){$('builder-error').textContent=error.message;$('builder-error').hidden=false;}
 finally{button.disabled=false;button.firstElementChild.textContent='Build my practice';}
}
$('replace-cancel').addEventListener('click',()=>{$('replace-dialog').close();pendingBuild=false;});
$('replace-confirm').addEventListener('click',()=>{$('replace-dialog').close();if(pendingBuild){pendingBuild=false;build();}});
$('replace-save').addEventListener('click',exportAnswers);
function link(text,url){const a=el('a','',text);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
function scoreSelect(max,value,onChange,id){const select=el('select');select.id=id;select.add(new Option('Not marked',''));for(let i=0;i<=max;i++)select.add(new Option(`${i} / ${max}`,i));select.value=value??'';select.addEventListener('change',()=>onChange(select.value));return select;}
function render(){
 document.dispatchEvent(new CustomEvent('practice-timer:set-paper',{detail:{id:paper?.id||null,minutes:paper?.minutes||null}}));
 if(!paper){$('paper-questions').replaceChildren();$('pdf-token').value='';$('teacher-email').value='';$('student-name').value='';$('email-answers').checked=false;$('email-note').textContent='';$('paper-section').hidden=true;$('empty-state').hidden=false;$('ready-state').hidden=true;return;}
 $('paper-section').hidden=false;$('empty-state').hidden=true;$('ready-state').hidden=false;
 $('ready-summary').textContent=`${paper.questions.length} questions · ${paper.total_marks} marks`;
 $('paper-title').textContent=paper.title;$('paper-meta').textContent=`${paper.component_name} · ${paper.questions.length} questions · ${paper.total_marks} marks`+(paper.minutes?` · ${paper.minutes/60} hour${paper.minutes===120?'s':''}`:'')+' · Unofficial practice';
 $('pdf-token').value=paper.token;
 const container=$('paper-questions');container.replaceChildren();
 paper.questions.forEach((q,index)=>{
  if(!q.examiner_report_url){const source=q.source_label||'',exact=q.source_type!=='additional'?examinerReports.find(r=>source.includes(String(r.year))&&source.toLowerCase().includes(r.series.toLowerCase())):null;const r=exact||examinerReports[0];if(r)Object.assign(q,{examiner_report_url:r.url,examiner_report_title:r.title,examiner_report_note:exact?'Matches the original exam series. This report covers the wider qualification; use the mark scheme to award marks.':'General examiner advice from '+r.series+' '+r.year+'; this is not a report on this practice set.'});}

  const k=key(q),card=el('article','question-card part-'+q.part);
  const header=el('div','question-header'),label=el('div','question-label');
  label.append(el('span','question-number',paper.mode==='full'?`${q.number}(${q.part})`:`${index+1} (${q.part})`),el('span','',q.topic));
  header.append(label,el('span','',`${q.marks} marks`+(q.spag?` + ${q.spag} SPaG`:'')));
  const prompt=el('div','question-prompt',q.prompt);prompt.id='prompt-'+index;
  const answerLabel=el('label','',`Your answer to question ${index+1}`);answerLabel.htmlFor='answer-'+index;
  const textarea=el('textarea');textarea.id='answer-'+index;textarea.setAttribute('aria-describedby',prompt.id);textarea.placeholder='Make a start. This space is yours.';textarea.value=answers[k]||'';textarea.maxLength=30000;
  textarea.addEventListener('input',()=>{answers[k]=textarea.value;persist();updateProgress();});
  const printLines=el('div','print-lines');const writingLines=q.answer_lines||((q.part==='d'&&['component-1-general','component-2-christianity'].includes(q.component)&&q.number===1)?48:({a:6,b:15,c:24,d:49}[q.part]));for(let i=0;i<writingLines;i++)printLines.append(el('div','print-line'));
  const source=el('p','question-source',q.source_label);
  if(q.kind==='question'){source.append(document.createTextNode(' · '),link('Report an issue','/feedback/?question='+encodeURIComponent(q.id)));}
  if(q.original_paper_url){source.append(document.createTextNode(' · '),link('Original question',q.original_paper_url));}
  const details=el('details','mark-scheme');details.append(el('summary','', 'Ready to self mark? Show marking guidance'));
  details.append(el('p','scheme-note',q.scheme_note),el('div','scheme-text',q.indicative_content));
  const links=el('div','scheme-links');
  if(q.rubric_url)links.append(link('Exact official band descriptors ↗',q.rubric_url));
  if(q.original_scheme_url)links.append(link(q.kind==='keyword'?'Official glossary ↗':'Original question mark scheme ↗',q.original_scheme_url));
  if(q.spag_rubric_url)links.append(link('SPaG descriptors ↗',q.spag_rubric_url));
  if(q.examiner_report_url){links.append(link(q.examiner_report_title||'Official examiner report ↗',q.examiner_report_url));details.append(el('p','scheme-note',q.examiner_report_note));}
  details.append(links);
  if(q.rubric_url){
   const tableButton=el('button','secondary-button','View band table here');tableButton.type='button';let iframe;
   tableButton.addEventListener('click',()=>{if(iframe){iframe.remove();iframe=null;tableButton.textContent='View band table here';}else{iframe=el('iframe','pdf-table');iframe.src=q.rubric_url;iframe.title=`Official ${q.part.toUpperCase()} marking bands for question ${index+1}`;iframe.loading='lazy';details.append(iframe);tableButton.textContent='Hide band table';}});details.append(tableButton);
  }
  const marking=el('div','self-mark'),scoreGroup=el('div');const sl=el('label','', 'My self mark');sl.htmlFor='mark-'+index;
  const score=scoreSelect(q.marks,marks[k],value=>{if(value==='')delete marks[k];else marks[k]=Number(value);persist();updateProgress();},'mark-'+index);
  scoreGroup.append(sl,score);marking.append(scoreGroup);
  if(q.spag){const sg=el('div');const spl=el('label','','My SPaG mark');spl.htmlFor='spag-'+index;sg.append(spl,scoreSelect(6,spagMarks[k],value=>{if(value==='')delete spagMarks[k];else spagMarks[k]=Number(value);persist();updateProgress();},'spag-'+index));marking.append(sg);}
  details.append(marking);card.append(header,prompt,answerLabel,textarea,el('p','answer-caption','Saved in this browser tab. No automatic marking.'),printLines,source,details);container.append(card);
 });updateProgress();
}
function updateProgress(){if(!paper)return;const answered=paper.questions.filter(q=>(answers[key(q)]||'').trim()).length;const marked=paper.questions.filter(q=>marks[key(q)]!==undefined).length;const spagCount=paper.questions.filter(q=>q.spag&&spagMarks[key(q)]!==undefined).length;const expectedSpag=paper.questions.filter(q=>q.spag).length;const total=paper.questions.reduce((sum,q)=>sum+(marks[key(q)]||0)+(spagMarks[key(q)]||0),0);$('progress-fill').style.width=(answered/paper.questions.length*100)+'%';$('progress-text').textContent=`${answered} / ${paper.questions.length} answered · ${marked} marked`;$('score-summary').textContent=marked||spagCount?`${total} / ${paper.total_marks} marks ${marked===paper.questions.length&&spagCount===expectedSpag?'· Self marking complete':'· Marking in progress'}`:'Mark your answers when you’re ready.';}
function download(text,filename,type='text/plain'){const url=URL.createObjectURL(new Blob([text],{type}));const a=el('a');a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);}
function answerText(){return paper.title+'\n'+paper.component_name+'\nUnofficial practice · '+new Date().toLocaleDateString('en-GB')+'\n\n'+paper.questions.map((q,i)=>`${i+1}. ${q.prompt}\n[${q.marks} marks${q.spag?' + 6 SPaG':''}]\n\n${answers[key(q)]||'(No answer typed)'}\n\nSelf mark: ${marks[key(q)]===undefined?'Not marked':marks[key(q)]+'/'+q.marks}${q.spag?'\nSPaG: '+(spagMarks[key(q)]===undefined?'Not marked':spagMarks[key(q)]+'/6'):''}`).join('\n\n-------------------------\n\n');}
function exportAnswers(){if(!paper)return;download(answerText(),'rerevi-my-answers.txt');toast('Answers saved. Keep this file if you want to return to your work.');}
function exportPracticeFile(){
 if(!paper)return;
 const title=$('practice-file-title').value.trim()||paper.title;
 const reference='PR-'+String(paper.id||'practice').slice(0,12).toUpperCase();
 const print={theme:$('pdf-theme').value,cover:$('pdf-cover').checked,back_pages:Number($('pdf-back-pages').value),layout:'standard',breaks:'none',extra_lines:0,continuation_pages:2,identity_fields:true,duplex:false,lined_questions:true};
 const snapshot={id:paper.id,title,component:paper.component,component_name:paper.component_name,mode:paper.mode,minutes:paper.minutes,total_marks:paper.total_marks,instructions:paper.instructions||'Answer the selected questions.',reference,questions:structuredClone(paper.questions)};
 const data={format:'rerevi.practice',version:1,exported_at:new Date().toISOString(),paper:snapshot,position:0,settings:{title,instructions:snapshot.instructions,component:paper.component,parts:[...new Set(paper.questions.map(q=>q.part))],print}};
 if($('practice-file-work').checked){
  const selectedKeys=new Set(paper.questions.map(key));
  const selectedWork=values=>Object.fromEntries(Object.entries(values).filter(([k])=>selectedKeys.has(k)));
  data.work={answers:selectedWork(answers),plans:{},marks:selectedWork(marks),spagMarks:selectedWork(spagMarks),flags:{},include:{}};
 }
 const contents=JSON.stringify(data,null,2);
 if(new Blob([contents]).size>2000000){toast('This practice file is larger than the 2 MB import limit. Try exporting without answers.');return;}
 download(contents,(title.replace(/[^a-z0-9_-]+/gi,'-').slice(0,65)||'practice')+'.rerevi','application/json');
 $('export-practice-dialog').close();toast('Practice file saved. Use Import .rerevi file in the sidebar to reopen it.');
}
$('export-practice').addEventListener('click',()=>{if(!paper)return;$('practice-file-title').value=paper.title;$('practice-file-work').checked=false;$('export-practice-dialog').showModal();});
$('practice-file-cancel').addEventListener('click',()=>$('export-practice-dialog').close());
$('practice-file-download').addEventListener('click',exportPracticeFile);
$('open-worksheet').addEventListener('click',()=>{if(paper){try{sessionStorage.setItem('rerevi-worksheet-handoff',JSON.stringify({paper,answers,marks,spagMarks,print:{theme:$('pdf-theme').value,cover:$('pdf-cover').checked,back_pages:Number($('pdf-back-pages').value)}}));window.location.href='/worksheets/';}catch{toast('Browser storage is unavailable. Open the worksheet workspace from navigation instead.');}}});
window.addEventListener('beforeunload',event=>{if(paper&&hasWork()){event.preventDefault();event.returnValue='';}});
function submitPaperPdf(printable=false){
 if(!paper)return;
 $('pdf-theme-value').value=$('pdf-theme').value;
 $('pdf-cover-value').value=$('pdf-cover').checked?'1':'0';
 $('pdf-back-pages-value').value=$('pdf-back-pages').value;
 $('pdf-presentation').value=printable?'print':'download';
 $('pdf-form').target=printable?'_blank':'_self';
 $('pdf-form').submit();
 if(printable)toast('Print-ready PDF opened in a new tab. Use its printer button or Ctrl/Cmd+P.');
}
$('export-answers').addEventListener('click',exportAnswers);
$('download-pdf').addEventListener('click',()=>submitPaperPdf(false));
$('print-paper').addEventListener('click',()=>submitPaperPdf(true));$('jump-paper').addEventListener('click',()=>$('paper-section').scrollIntoView({behavior:'smooth'}));
$('clear-draft').addEventListener('click',()=>{if(shareBusy){toast('Wait for the sharing request to finish before clearing this practice.');return;}$('clear-dialog').showModal();});$('clear-cancel').addEventListener('click',()=>$('clear-dialog').close());$('clear-confirm').addEventListener('click',()=>{$('clear-dialog').close();paper=null;answers={};marks={};spagMarks={};shared=null;$('share-opt-in').checked=false;updateShare();try{sessionStorage.removeItem(STORAGE);}catch{}render();toast('This practice has been cleared.');});
$('email-teacher').addEventListener('click',()=>{
 if(!paper)return;const address=$('teacher-email');if(!address.value.trim()||!address.checkValidity()){address.reportValidity();address.focus();return;}
 const name=$('student-name').value.trim();let body=`Hello,\n\nCould you please give me feedback on my ${paper.title.toLowerCase()} (${paper.component_name})? I would appreciate advice on what I did well and how to improve.\n`;
 if(shared&&$('email-share').checked&&new Date(shared.expires_at)>new Date())body+='\nShared answer snapshot (read-only):\n'+shared.url+'\nAvailable until '+new Date(shared.expires_at).toLocaleString('en-GB')+'.\n';
 if($('email-answers').checked)body+='\nMy practice and answers:\n\n'+answerText();
 body+='\n\nThank you'+(name?',\n'+name:'.');
 const subject='RE practice — feedback request';let uri='mailto:'+encodeURIComponent(address.value.trim())+'?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(body);
 if(uri.length>1800){exportAnswers();body=`Hello,\n\nCould you please give me feedback on my ${paper.title.toLowerCase()} (${paper.component_name})? I have downloaded my answers and will attach them to this email.${shared&&$('email-share').checked?'\n\nShared answer snapshot: '+shared.url:''}\n\nThank you${name?',\n'+name:'.'}`;uri='mailto:'+encodeURIComponent(address.value.trim())+'?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(body);$('email-note').textContent='Your answers were too long for an email link. They have been downloaded. Attach rerevi-my-answers.txt to the draft before sending.';}else{$('email-note').textContent='Your email app will open a draft. Review it, then send when you’re ready. If no email app opens, save your answers and create the email manually.';}
 window.location.href=uri;
});
function deletionURL(){return shared?new URL('/s/manage/',shared.url).href+'#'+shared.token+'.'+shared.delete_token:'';}
function updateShare(){
 const opted=$('share-opt-in').checked;
 $('share-controls').hidden=!opted&&!shared;
 $('create-share').disabled=shareBusy||!opted;
 $('create-share').textContent=shareBusy?'Please wait…':shared?'Create replacement link':'Create answer link';
 $('share-result').hidden=!shared;
 if(shared){
  $('share-url').value=shared.url;$('open-share').href=shared.url;
  const deletion=deletionURL();$('deletion-url').value=deletion;
  $('email-deletion').href='mailto:?subject='+encodeURIComponent('RE Revi: my private submission deletion link')+'&body='+encodeURIComponent('Keep this private. Use this link to permanently delete my shared answers, even after closing the practice tab:\n\n'+deletion+'\n\nExpires: '+new Date(shared.expires_at).toLocaleString('en-GB')+'.\nDo not forward this deletion link to anyone else.');
  $('share-expiry').textContent='Expires '+new Date(shared.expires_at).toLocaleString('en-GB')+'. Stored answers are deleted automatically within 30 days of creation.';
 }
 if(!shared){$('share-url').value='';$('open-share').removeAttribute('href');$('deletion-url').value='';$('email-deletion').removeAttribute('href');}
 if(!paper)$('share-status').textContent='';
 $('email-share').disabled=!opted||!shared||(shared&&new Date(shared.expires_at)<=new Date());
 if(!opted)$('email-share').checked=false;
}
$('share-opt-in').addEventListener('change',updateShare);
$('create-share').addEventListener('click',async()=>{
 if(!paper||!$('share-opt-in').checked||shareBusy)return;
 shareBusy=true;updateShare();$('share-status').textContent='';
 try{
  const response=await fetch('/api/shares/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify({consent:true,paper_token:paper.token,days:Number($('share-days').value),name:$('student-name').value.trim(),answers,marks,spag_marks:spagMarks,previous_share:shared?{token:shared.token,delete_token:shared.delete_token}:null})});
  let result;try{result=await response.json();}catch{throw new Error('The server could not create a link. Please try again.');}
  if(!response.ok)throw new Error(result.error||'Could not share these answers.');
  const previous=shared;shared=result;persist();$('email-share').checked=true;
  $('share-status').textContent='Link created. Save your private deletion link below before closing this tab.'+(previous&&!result.previous_deleted?' The previous link was unavailable; any remaining copy will follow its original expiry.':'');
  toast('Your answer-sharing link is ready.');
 }catch(error){$('share-status').textContent=error.message;}
 finally{shareBusy=false;updateShare();}
});
$('copy-deletion').addEventListener('click',async()=>{
 if(!shared)return;
 try{await navigator.clipboard.writeText(deletionURL());toast('Private deletion link copied. Keep it safe.');}
 catch{$('deletion-url').focus();$('deletion-url').select();toast('Select and copy your private deletion link.');}
});
$('send-receipt').addEventListener('click',async()=>{
 if(!shared)return;
 const email=$('receipt-email'),button=$('send-receipt');
 if(!email.value.trim()||!email.checkValidity()){email.reportValidity();$('receipt-status').textContent='Enter your own valid email address.';return;}
 button.disabled=true;$('receipt-status').textContent='Queueing your receipt…';
 try{
  const response=await fetch('/s/manage/email-receipt/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify({token:shared.token,delete_token:shared.delete_token,email:email.value.trim()})});
  const result=await response.json();if(!response.ok)throw new Error(result.error||'Could not queue the receipt.');
  $('receipt-status').textContent=result.message;
 }catch(error){$('receipt-status').textContent=error.message||'Could not send email. Download your deletion details instead.';}
 finally{button.disabled=false;}
});
$('save-deletion').addEventListener('click',()=>{
 if(!shared)return;
 download('RE Revi — private submission deletion details\n\nKeep this file private. Anyone with this link can delete your submission.\n\nDeletion link:\n'+deletionURL()+'\n\nExpires: '+new Date(shared.expires_at).toLocaleString('en-GB')+'\n\nOpen the deletion link and confirm deletion. No login is needed.\nAutomatic expiry still applies if you lose this file.','rerevi-private-deletion-link.txt');
 toast('Private deletion details downloaded.');
});
$('copy-share').addEventListener('click',async()=>{
 if(!shared)return;
 try{await navigator.clipboard.writeText(shared.url);toast('Sharing link copied.');}
 catch{$('share-url').focus();$('share-url').select();toast('Select and copy the link from the field above.');}
});
$('delete-share').addEventListener('click',async()=>{
 if(!shared||shareBusy)return;const button=$('delete-share');button.disabled=true;shareBusy=true;updateShare();
 try{
  const response=await fetch('/api/shares/delete/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify({token:shared.token,delete_token:shared.delete_token})});
  if(!response.ok&&response.status!==404)throw new Error('The link could not be deleted. Please try again.');
  shared=null;$('email-share').checked=false;$('share-url').value='';$('share-status').textContent='Shared answers are no longer available. Your browser draft is unchanged.';persist();updateShare();toast('Sharing link deleted.');
 }catch(error){$('share-status').textContent=error.message;}
 finally{button.disabled=false;shareBusy=false;updateShare();}
});
updateOptions();
try{const saved=JSON.parse(sessionStorage.getItem(STORAGE)||'null');if(saved&&saved.version===1&&saved.paper&&Array.isArray(saved.paper.questions)&&saved.paper.questions.length<=51){paper=saved.paper;answers=saved.answers||{};marks=saved.marks||{};spagMarks=saved.spagMarks||{};shared=saved.shared||null;if(shared)$('share-opt-in').checked=true;render();}}catch{toast('Your previous draft could not be restored. You can create a new practice set.');}
updateShare();
})();
