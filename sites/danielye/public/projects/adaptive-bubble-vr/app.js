'use strict';
(() => {
 const canvas=document.getElementById('intent-field'),ctx=canvas.getContext('2d'),range=document.getElementById('range');
 const candidates=[[-1.65,-1.1],[-.8,-1.5],[.25,-1.2],[1.4,-1.15],[-1.8,.15],[-.65,-.1],[.3,.15],[1.45,.2],[-1.4,1.25],[-.3,1.3],[.65,1.1],[1.7,1.35]];
 let hand=[-.5,.65],motion=[0,0],mode='intent';
 const clamp=x=>Math.max(0,Math.min(1,x));
 function draw(){
  if(!ctx)return;
  const rect=canvas.getBoundingClientRect(),w=rect.width,h=rect.height,dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
  const R=Number(range.value),rho=clamp(candidates.filter(p=>Math.hypot(p[0]-hand[0],p[1]-hand[1])<R).length/12),wd=mode==='intent'?.7+.4*rho:1,wt=mode==='intent'?.3*(1-rho):0;
  const scores=candidates.map((p,i)=>{const x=p[0]-hand[0],y=p[1]-hand[1],d=Math.hypot(x,y),D=clamp(1-d/R),T=d?clamp((motion[0]*x+motion[1]*y)/d):0;return {i,score:wd*D+wt*T};});let winner=scores[0];for(const s of scores)if(s.score>winner.score)winner=s;
  const scale=Math.min(w/5,h/4.5),map=p=>[w/2+p[0]*scale,h/2+p[1]*scale],hp=map(hand);
  ctx.strokeStyle='#dfe2e9';ctx.lineWidth=1;for(let i=-3;i<=3;i++){ctx.beginPath();ctx.moveTo(w/2+i*scale,0);ctx.lineTo(w/2+i*scale,h);ctx.stroke();ctx.beginPath();ctx.moveTo(0,h/2+i*scale);ctx.lineTo(w,h/2+i*scale);ctx.stroke();}
  ctx.fillStyle='#8e7ab50a';ctx.strokeStyle='#b3a5c4';ctx.setLineDash([4,6]);ctx.beginPath();ctx.arc(hp[0],hp[1],R*scale,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.setLineDash([]);
  candidates.forEach((p,i)=>{const [x,y]=map(p),selected=i===winner.i;ctx.fillStyle=selected?(mode==='intent'?'#6ea73e':'#bf5577'):'#c2c3d2';ctx.beginPath();ctx.arc(x,y,selected?11:8,0,Math.PI*2);ctx.fill();if(selected){ctx.strokeStyle='#26334b';ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(x,y,17,0,Math.PI*2);ctx.stroke();}ctx.font=selected?'bold 11px Arial':'10px Arial';ctx.fillStyle='#41445b';ctx.textAlign='center';ctx.fillText(String(i+1).padStart(2,'0'),x,y-23);});
  if(motion[0]||motion[1]){const x=hp[0]+motion[0]*40,y=hp[1]+motion[1]*40;ctx.strokeStyle='#6d549b';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(...hp);ctx.lineTo(x,y);ctx.stroke();const a=Math.atan2(motion[1],motion[0]);ctx.beginPath();ctx.moveTo(x-9*Math.cos(a-.4),y-9*Math.sin(a-.4));ctx.lineTo(x,y);ctx.lineTo(x-9*Math.cos(a+.4),y-9*Math.sin(a+.4));ctx.stroke();}
  ctx.fillStyle='#171b31';ctx.beginPath();ctx.arc(...hp,5,0,Math.PI*2);ctx.fill();ctx.font='9px Arial';ctx.textAlign='left';ctx.fillText('YOU',hp[0]+10,hp[1]+4);
  document.getElementById('winner').textContent='Target '+String(winner.i+1).padStart(2,'0');document.getElementById('score').textContent=winner.score.toFixed(3);document.getElementById('density').textContent=rho.toFixed(2);document.getElementById('distance-weight').textContent=wd.toFixed(2);document.getElementById('direction-weight').textContent=wt.toFixed(2);document.getElementById('range-value').textContent=R.toFixed(1);
 }
 function move(next){const dx=next[0]-hand[0],dy=next[1]-hand[1],d=Math.hypot(dx,dy);if(d>1e-6)motion=[dx/d,dy/d];hand=next;draw();}
 canvas.addEventListener('pointermove',e=>{if(e.pointerType!=='mouse'&&!e.buttons)return;const b=canvas.getBoundingClientRect(),s=Math.min(b.width/5,b.height/4.5);move([(e.clientX-b.left-b.width/2)/s,(e.clientY-b.top-b.height/2)/s]);});
 canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);const b=canvas.getBoundingClientRect(),s=Math.min(b.width/5,b.height/4.5);move([(e.clientX-b.left-b.width/2)/s,(e.clientY-b.top-b.height/2)/s]);});
 canvas.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();let [x,y]=hand;x+=e.key==='ArrowRight'?.12:e.key==='ArrowLeft'?-.12:0;y+=e.key==='ArrowDown'?.12:e.key==='ArrowUp'?-.12:0;move([Math.max(-2.1,Math.min(2.1,x)),Math.max(-1.8,Math.min(1.8,y))]);});
 document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>{mode=b.dataset.mode;document.querySelectorAll('[data-mode]').forEach(x=>{const on=x===b;x.classList.toggle('selected',on);x.setAttribute('aria-pressed',String(on));});draw();}));
 range.addEventListener('input',draw);document.getElementById('clear-motion').addEventListener('click',()=>{motion=[0,0];draw();});document.getElementById('reset-demo').addEventListener('click',()=>{hand=[-.5,.65];motion=[0,0];range.value='2';draw();});new ResizeObserver(draw).observe(canvas);
})();
