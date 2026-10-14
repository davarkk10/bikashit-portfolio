'use strict';
const $ = id => document.getElementById(id);
const fmt = n => Number(n).toFixed(3);
let results, selectedCase = 1, selectedCondition = 'clean';
const conditions = {
  clean: {tag:'Original preprocessed images', explanation:'Unseen case groups, evaluated with the frozen checkpoint.'},
  blur: {tag:'Gaussian blur · σ = 2', explanation:'Boundaries become softer. A 7 × 7 Gaussian kernel is applied to the resized input.'},
  noise: {tag:'Additive Gaussian noise · σ = 20', explanation:'Pixel intensities are perturbed on a 0–255 scale and clipped. This is not a physics-faithful speckle simulation.'}
};
function updateSummary(condition) {
  const summary = results.summary[condition];
  $('condition-tag').textContent = conditions[condition].tag;
  $('condition-dice').textContent = fmt(summary.patient_mean_dice);
  $('condition-explanation').textContent = conditions[condition].explanation;
  document.querySelectorAll('[data-summary]').forEach(b => {
    const active = b.dataset.summary === condition;
    b.classList.toggle('active',active); b.setAttribute('aria-pressed',String(active));
  });
  document.querySelectorAll('.bar-row').forEach(b => b.classList.toggle('active',b.dataset.condition===condition));
}
function updateExample() {
  const example = results.examples[selectedCase], image = example.conditions[selectedCondition];
  $('example-id').textContent = example.id.toUpperCase();
  $('example-selection').textContent = example.selection;
  $('example-raw').src = image.image;
  $('example-raw').alt = `${selectedCondition} ultrasound image ${example.id}, held out from training`;
  $('example-overlay').src = image.overlay;
  $('example-overlay').alt = `Mint reference and amber model contours for ${example.id} under ${selectedCondition}`;
  $('example-dice').textContent = fmt(image.dice);
  $('example-iou').textContent = `IoU ${fmt(image.iou)}`;
  document.querySelectorAll('[data-case]').forEach(b=>{
    const active = Number(b.dataset.case)===selectedCase;
    b.classList.toggle('active',active); b.setAttribute('aria-pressed',String(active));
  });
  document.querySelectorAll('[data-example-condition]').forEach(b=>{
    const active = b.dataset.exampleCondition===selectedCondition;
    b.classList.toggle('active',active); b.setAttribute('aria-pressed',String(active));
  });
}
function setupResults() {
  const clean = results.summary.clean;
  $('main-dice').textContent = fmt(clean.patient_mean_dice);
  $('main-ci').textContent = clean.patient_bootstrap_95ci_dice.map(fmt).join('–');
  $('image-dice').textContent = fmt(clean.image_mean_dice);
  $('image-iou').textContent = fmt(clean.image_mean_iou);
  $('blur-drop').textContent = '−'+fmt(-results.paired_case_delta.blur);
  $('noise-drop').textContent = '−'+fmt(-results.paired_case_delta.noise);
  $('failure-copy').textContent = `${results.n_below_05} of ${results.test_images} test images have clean Dice below 0.5. The distribution shows why a mean alone is incomplete.`;
  for (const condition of ['clean','blur','noise']) {
    const row=document.createElement('div'); row.className='bar-row';row.dataset.condition=condition;
    const label=document.createElement('span');label.textContent=condition[0].toUpperCase()+condition.slice(1);
    const track=document.createElement('div');track.className='bar-track';
    const fill=document.createElement('div');fill.className='bar-fill';fill.style.width=`${results.summary[condition].patient_mean_dice*100}%`;
    track.append(fill);
    const value=document.createElement('span');value.textContent=fmt(results.summary[condition].patient_mean_dice);
    row.append(label,track,value);$('score-bars').append(row);
  }
  results.examples.forEach((example,index)=>{
    const b=document.createElement('button');b.dataset.case=index;
    const title=document.createElement('span');title.textContent=example.selection.split(' · ')[0];
    const sub=document.createElement('small');sub.textContent=example.id+' · clean Dice '+fmt(example.conditions.clean.dice);
    b.append(title,sub);b.addEventListener('click',()=>{selectedCase=index;updateExample();});
    $('case-buttons').append(b);
  });
  const max=Math.max(...results.histogram);
  results.histogram.forEach((count,index)=>{
    const b=document.createElement('button');b.className='hist-bar';b.style.height=`${Math.max(1,count/max*88)}%`;
    const text=`Dice ${(index/10).toFixed(1)}–${((index+1)/10).toFixed(1)}: ${count} images`;
    b.title=text;b.setAttribute('aria-label',text);
    const value=document.createElement('span');value.textContent=count;b.append(value);
    b.addEventListener('click',()=>{$('histogram').nextElementSibling.nextElementSibling.textContent=text;});
    $('histogram').append(b);
  });
  results.subgroups.forEach(group=>{
    const p=document.createElement('p');p.textContent=`${group.name[0].toUpperCase()+group.name.slice(1)} · ${group.images} images`;
    const n=document.createElement('strong');n.textContent=fmt(group.image_mean_dice);p.append(n);$('subgroups').append(p);
  });
  const median=results.examples[1];$('hero-image').src=median.conditions.clean.overlay;
  $('hero-case').textContent='MEDIAN CASE / '+median.id;
  $('hero-image').alt=`Median-scoring held-out ultrasound case ${median.id}, with mint reference and amber predicted contours`;
  document.querySelectorAll('[data-summary]').forEach(b=>b.addEventListener('click',()=>updateSummary(b.dataset.summary)));
  document.querySelectorAll('[data-example-condition]').forEach(b=>b.addEventListener('click',()=>{selectedCondition=b.dataset.exampleCondition;updateExample();}));
  $('show-worst').addEventListener('click',()=>{selectedCase=3;selectedCondition='clean';updateExample();$('explore').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});$('case-buttons').children[3].focus({preventScroll:true});});
  $('overlay-opacity').addEventListener('input',event=>{$('example-overlay').style.opacity=Number(event.target.value)/100;$('opacity-value').value=event.target.value+'%';});
  $('example-dice').setAttribute('aria-live','polite');$('condition-explanation').setAttribute('aria-live','polite');
  updateSummary('clean');updateExample();
}
function drawDice() {
  const canvas=$('dice-canvas'),ctx=canvas.getContext('2d'),offset=Number($('toy-offset').value);
  const truth={x:165,y:145,rx:72,ry:86},pred={x:165+offset,y:145,rx:80,ry:72};
  let t=0,p=0,intersection=0;
  for(let y=0;y<canvas.height;y++)for(let x=0;x<canvas.width;x++){
    const a=((x-truth.x)/truth.rx)**2+((y-truth.y)/truth.ry)**2<=1;
    const b=((x-pred.x)/pred.rx)**2+((y-pred.y)/pred.ry)**2<=1;
    if(a)t++;if(b)p++;if(a&&b)intersection++;
  }
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.strokeStyle='#c9d5c3';ctx.lineWidth=.5;
  for(let x=0;x<canvas.width;x+=24){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,canvas.height);ctx.stroke();}
  for(let y=0;y<canvas.height;y+=24){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(canvas.width,y);ctx.stroke();}
  for(const [shape,fill,stroke] of [[truth,'rgba(32,160,126,.24)','#21876c'],[pred,'rgba(201,154,50,.28)','#ad8030']]){
    ctx.beginPath();ctx.ellipse(shape.x,shape.y,shape.rx,shape.ry,0,0,Math.PI*2);ctx.fillStyle=fill;ctx.fill();ctx.strokeStyle=stroke;ctx.lineWidth=2;ctx.stroke();
  }
  ctx.font='12px monospace';ctx.fillStyle='#235443';ctx.fillText('REFERENCE',60,270);ctx.fillStyle='#896522';ctx.fillText('PREDICTION',270,270);
  $('toy-dice').textContent=fmt(2*intersection/(t+p));
  canvas.setAttribute('aria-label',`Illustrative mask overlap; Dice ${fmt(2*intersection/(t+p))}, prediction offset ${offset} pixels.`);
}
$('toy-offset').addEventListener('input',drawDice);drawDice();
fetch('assets/results.json').then(response=>{if(!response.ok)throw new Error('Results unavailable');return response.json();}).then(data=>{results=data;setupResults();}).catch(()=>{$('load-error').hidden=false;});
