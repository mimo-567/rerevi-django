'use strict';
(() => {
 const root=document.querySelector('[data-practice-timer]');if(!root)return;
 const find=name=>root.querySelector('[data-timer-'+name+']');
 const display=find('display'),minutes=find('minutes'),start=find('start'),pause=find('pause'),reset=find('reset'),suggested=find('suggested'),status=find('status');
 const storage='practice-countdown-v1:'+root.dataset.timerKey;
 let state={duration:25*60000,remaining:25*60000,deadline:null,running:false,paper:null,suggested:null,finished:false,warned:false};
 let storageWarning=false;
 function save(){try{sessionStorage.setItem(storage,JSON.stringify(state));}catch{if(!storageWarning){storageWarning=true;status.textContent='Timer works here, but browser storage is unavailable: refreshing will reset it.';}}}
 function remaining(){return state.running?Math.max(0,state.deadline-Date.now()):state.remaining;}
 function formatted(value){const total=Math.ceil(Math.max(0,value)/1000),seconds=total%60,mins=Math.floor(total/60)%60,hours=Math.floor(total/3600);return (hours?String(hours).padStart(2,'0')+':':'')+String(mins).padStart(2,'0')+':'+String(seconds).padStart(2,'0');}
 function render(){
  const value=remaining();display.textContent=formatted(value);display.setAttribute('aria-label',formatted(value)+' remaining');
  start.disabled=state.running||value<=0;start.textContent=state.finished?'Finished':value<state.duration?'Resume':'Start';pause.disabled=!state.running;
  root.classList.toggle('timer-running',state.running);root.classList.toggle('timer-finished',state.finished);root.classList.toggle('timer-low',value>0&&value<=5*60000);
  minutes.disabled=state.running;suggested.hidden=!state.suggested;suggested.textContent='Use paper time ('+state.suggested+' min)';
 }
 function tick(){
  const value=remaining();
  if(state.running&&value<=0){state.running=false;state.remaining=0;state.deadline=null;state.finished=true;save();status.textContent='Time is up. Your answers are safe; you can keep working or reset the timer.';}
  else if(state.running&&!state.warned&&state.duration>=10*60000&&value<=5*60000){state.warned=true;save();status.textContent='Five minutes remaining.';}
  render();
 }
 function setDuration(value,message){state.duration=value*60000;state.remaining=state.duration;state.deadline=null;state.running=false;state.finished=false;state.warned=false;minutes.value=value;save();status.textContent=message;render();}
 function changeDuration(value,message){
  if(!Number.isInteger(value)||value<1||value>360){minutes.value=state.duration/60000;status.textContent='Choose a whole number of minutes between 1 and 360.';return;}
  if(remaining()<state.duration&&!state.finished&&!confirm('Reset the timer to '+value+' minutes? Your answers will stay unchanged.')){minutes.value=state.duration/60000;return;}
  setDuration(value,message);
 }
 minutes.addEventListener('change',()=>changeDuration(Number(minutes.value),'Duration set. Press Start when ready.'));
 start.addEventListener('click',()=>{if(state.running||remaining()<=0)return;const value=Number(minutes.value);if(!Number.isInteger(value)||value<1||value>360){status.textContent='Choose 1–360 whole minutes.';return;}if(value*60000!==state.duration){changeDuration(value,'Duration set.');if(value*60000!==state.duration)return;}state.deadline=Date.now()+state.remaining;state.running=true;state.finished=false;save();status.textContent='Timer running. You can pause it at any time.';tick();});
 pause.addEventListener('click',()=>{if(!state.running)return;const value=remaining();if(value<=0){tick();return;}state.remaining=value;state.running=false;state.deadline=null;save();status.textContent='Paused. Press Resume to continue.';render();});
 reset.addEventListener('click',()=>{if((state.running||remaining()<state.duration)&&!state.finished&&!confirm('Reset the timer? Your answers will stay unchanged.'))return;setDuration(state.duration/60000,'Timer reset. Press Start when ready.');});
 suggested.addEventListener('click',()=>{if(state.suggested)changeDuration(state.suggested,'Paper time selected. Press Start when ready.');});
 document.addEventListener('practice-timer:set-paper',event=>{
  const paper=event.detail||{};const id=typeof paper.id==='string'?paper.id:null;
  const recommendation=Number.isInteger(paper.minutes)&&paper.minutes>=1&&paper.minutes<=360?paper.minutes:null;
  if(state.paper===id){state.suggested=recommendation;save();render();return;}
  state.paper=id;state.suggested=recommendation;
  setDuration(recommendation||state.duration/60000,id?'Timer ready for this practice set. Press Start when ready.':'Practice cleared. Timer reset.');
 });
 try{
  const saved=JSON.parse(sessionStorage.getItem(storage)||'null');
  if(saved&&Number.isInteger(saved.duration)&&saved.duration>=60000&&saved.duration<=360*60000&&Number.isFinite(saved.remaining)&&saved.remaining>=0&&saved.remaining<=saved.duration&&typeof saved.running==='boolean'&&(!saved.running||(Number.isFinite(saved.deadline)&&saved.deadline<=Date.now()+saved.duration+60000))&&(saved.paper===null||typeof saved.paper==='string')){
   state={duration:saved.duration,remaining:saved.remaining,deadline:saved.running?saved.deadline:null,running:saved.running,paper:saved.paper,suggested:Number.isInteger(saved.suggested)&&saved.suggested>=1&&saved.suggested<=360?saved.suggested:null,finished:!!saved.finished,warned:!!saved.warned};
   status.textContent=state.running?'Timer restored and running.':state.finished?'Time is up. Your answers are safe.':'Timer restored. Press '+(state.remaining<state.duration?'Resume':'Start')+' when ready.';
  }
 }catch{status.textContent='Previous timer could not be restored. Choose a duration to start again.';}
 minutes.value=state.duration/60000;
 document.addEventListener('visibilitychange',tick);window.addEventListener('pageshow',tick);setInterval(tick,250);tick();
})();
