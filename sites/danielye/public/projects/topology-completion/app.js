'use strict';
(() => {
 const canvas=document.getElementById('cloud'),ctx=canvas.getContext('2d');
 const modeButtons=[...document.querySelectorAll('[data-mode]')],selector=document.getElementById('sample');
 let data,mode='target',yaw=-.42,pitch=-.63,zoom=1,drag=null,width=0,height=0;
 const labels={target:'Complete target',partial:'Partial input',overlay:'Input + target'};
 function render(){
  if(!ctx)return;
  const box=canvas.getBoundingClientRect(),dpr=Math.min(window.devicePixelRatio||1,2);width=box.width;height=box.height;
  canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);
  if(!data)return;
  const sample=data.samples[Number(selector.value)],sets=mode==='overlay'?[['target','#b4d58a',.42],['partial','#e9a8c8',.95]]:[[mode,mode==='target'?'#cbe99d':'#e9a8c8',.9]];
  const cloud=sample.target.points,center=[0,1,2].map(i=>(Math.min(...cloud.map(p=>p[i]))+Math.max(...cloud.map(p=>p[i])))/2);
  const extent=Math.max(...[0,1,2].map(i=>Math.max(...cloud.map(p=>p[i]))-Math.min(...cloud.map(p=>p[i]))));
  const scale=Math.min(width*.83,height*.86)/extent*zoom,points=[];
  for(const [key,color,alpha] of sets)for(const p of sample[key].points){const x=p[0]-center[0],y=p[1]-center[1],z=p[2]-center[2];const a=x*Math.cos(yaw)+z*Math.sin(yaw),b=-x*Math.sin(yaw)+z*Math.cos(yaw);const v=y*Math.cos(pitch)-b*Math.sin(pitch),depth=y*Math.sin(pitch)+b*Math.cos(pitch);points.push({x:width/2+a*scale,y:height/2-v*scale,z:depth,color,alpha});}
  points.sort((a,b)=>a.z-b.z);for(const p of points){ctx.globalAlpha=p.alpha;ctx.fillStyle=p.color;ctx.beginPath();ctx.arc(p.x,p.y,Math.max(.8,Math.min(1.8,width/300)),0,Math.PI*2);ctx.fill();}ctx.globalAlpha=1;
  document.getElementById('cloud-label').textContent=labels[mode];document.getElementById('cloud-count').textContent=mode==='overlay'?`${sample.partial.count} input / ${sample.target.count} target`:`${sample[mode].count.toLocaleString()} points`;
  document.querySelector('.scene-index').textContent=`0${Number(selector.value)+1} / 03`;
 }
 modeButtons.forEach(b=>b.addEventListener('click',()=>{mode=b.dataset.mode;modeButtons.forEach(x=>{x.classList.toggle('selected',x===b);x.setAttribute('aria-pressed',String(x===b));});render();}));
 selector.addEventListener('change',render);
 document.getElementById('reset').addEventListener('click',()=>{yaw=-.42;pitch=-.63;zoom=1;render();});
 canvas.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);});
 canvas.addEventListener('pointermove',e=>{if(!drag)return;yaw+=(e.clientX-drag[0])*.008;pitch=Math.max(-1.5,Math.min(1.5,pitch+(e.clientY-drag[1])*.008));drag=[e.clientX,e.clientY];render();});
 canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);
 canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.55,Math.min(2.4,zoom*Math.exp(-e.deltaY*.001)));render();},{passive:false});
 canvas.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','-','=','Home'].includes(e.key))return;e.preventDefault();if(e.key==='ArrowLeft')yaw-=.1;if(e.key==='ArrowRight')yaw+=.1;if(e.key==='ArrowUp')pitch-=.1;if(e.key==='ArrowDown')pitch+=.1;if(e.key==='+'||e.key==='=')zoom=Math.min(2.4,zoom*1.1);if(e.key==='-')zoom=Math.max(.55,zoom/1.1);if(e.key==='Home'){yaw=-.42;pitch=-.63;zoom=1;}render();});
 new ResizeObserver(render).observe(canvas);
 fetch('assets/pointclouds.json').then(r=>{if(!r.ok)throw Error('Data unavailable');return r.json();}).then(d=>{data=d;render();}).catch(()=>{document.getElementById('cloud-error').hidden=false;document.getElementById('cloud-count').textContent='Data unavailable';});
})();
