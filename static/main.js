const btn=document.getElementById('scoreBtn');
const tx=document.getElementById('transcript');
const fI=document.getElementById('fileInput');
const out=document.getElementById('out');

fI.addEventListener('change',async(e)=>{
 const f=e.target.files[0];
 if(!f)return;
 tx.value=await f.text();
});

btn.addEventListener('click',async()=>{
 const t=tx.value.trim();
 if(!t){alert('Paste text');return;}
 out.innerHTML='<div class="result">Scoring...</div>';
 try{
  const r=await fetch('/api/score',{
   method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({transcript:t})
  });
  const j=await r.json();
  if(j.error){out.innerHTML=j.error;return;}
  render(j);
 }catch(e){out.innerHTML='Error: '+e.message;}
});

function render(j){
 let h=`<div class="result">
 <h3>Overall: ${j.overall_score}</h3>
 Words: ${j.word_count}
 <table><tr><th>Criterion</th><th>Score</th><th>Kws</th><th>Sem</th><th>Len</th></tr>`;
 j.per_criterion.forEach(c=>{
  h+=`<tr>
   <td>${c.criterion}</td>
   <td>${c.criterion_score}</td>
   <td>${c.found_keywords.join(', ')}</td>
   <td>${c.semantic_similarity}</td>
   <td>${c.length_fraction}</td>
  </tr>`;
 });
 h+='</table></div>';
 out.innerHTML=h;
}
