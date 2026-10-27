'use strict';
(() => {
 const form=document.getElementById('submission-delete-form');
 const input=document.getElementById('recovery-link');
 const status=document.getElementById('deletion-status');
 const button=document.getElementById('confirm-delete-button');
 const pattern=/^[A-Za-z0-9_-]{43}\.[A-Za-z0-9_-]{43}$/;
 // URL fragments are not sent to the server or included in HTTP access logs.
 if(location.hash){
  const fragment=location.hash.slice(1);
  if(pattern.test(fragment)){
   input.value=location.origin+location.pathname+'#'+fragment;
   document.getElementById('deletion-ready').textContent='Your private deletion key is loaded. Confirm below to remove this submission.';
  }else status.textContent='This deletion link is invalid. Paste the full private link from your saved file or email.';
  history.replaceState(null,'',location.pathname);
 }
 form.addEventListener('submit',async event=>{
  event.preventDefault();
  let secret;
  try{
   const url=new URL(input.value.trim());
   if(url.origin!==location.origin||url.pathname!=='/s/manage/')throw new Error();
   secret=url.hash.slice(1);
   if(!pattern.test(secret))throw new Error();
  }catch{status.textContent='Paste the complete private deletion link saved from this website. The teacher viewing link cannot delete a submission.';return;}
  if(!document.getElementById('confirm-deletion').checked)return;
  const [token,delete_token]=secret.split('.');
  button.disabled=true;status.textContent='Deleting…';
  try{
   const response=await fetch('/s/manage/delete/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':form.querySelector('[name=csrfmiddlewaretoken]').value},body:JSON.stringify({token,delete_token})});
   if(response.status===404){status.textContent='The submission has already expired or been deleted, or this private deletion key is invalid.';button.disabled=false;return;}
   if(!response.ok)throw new Error();
   form.hidden=true;input.value='';status.textContent='Your shared submission has been permanently deleted. Its viewing link no longer works.';
  }catch{status.textContent='Could not delete the submission. Check your connection and try again.';button.disabled=false;}
 });
})();
