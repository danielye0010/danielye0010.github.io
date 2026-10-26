'use strict';
(() => {
  const $ = s => document.querySelector(s);
  const labels = {reference:'Reference / Four-hole solid',deformed:'Deformed / Nonlinear Q1 map','cut-first':'A / Cut, then deform','cut-after':'B / Deform, then cut',transported:'C / Cut with the transported tool'};
  const colors = {reference:[.53,.55,.62],deformed:[.48,.40,.66],'cut-first':[.48,.36,.66],'cut-after':[.66,.42,.26],transported:[.25,.48,.54]};
  let models={},buffers={},current='cut-after',requestId=0,angle=-2.40,elevation=.58,distance=2.35,target=[.5,.5,.5],detail=false;
  const canvas=$('#solid'),gl=canvas.getContext('webgl',{antialias:true,alpha:true,preserveDrawingBuffer:true});
  let program,position,normal,uniforms={};
  function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
  function initialize(){
    if(!gl)throw Error('WebGL unavailable');
    program=gl.createProgram();
    gl.attachShader(program,shader(gl.VERTEX_SHADER,`attribute vec3 position;attribute vec3 normal;uniform vec3 target;uniform vec3 right;uniform vec3 up;uniform vec3 front;uniform float distance;uniform float aspect;varying vec3 n;varying vec3 world;void main(){vec3 p=position-target;float x=dot(p,right),y=dot(p,up),z=dot(p,front)-distance;gl_Position=vec4(2.2*x/aspect,2.2*y,-1.001*z-.02001,-z);n=normal;world=position;}`));
    gl.attachShader(program,shader(gl.FRAGMENT_SHADER,`precision highp float;uniform vec3 color;uniform float clipZ;varying vec3 n;varying vec3 world;void main(){if(world.z>clipZ)discard;vec3 v=normalize(n);float l=abs(dot(v,normalize(vec3(.4,-.65,1.))));float rim=pow(abs(v.z),1.5);vec3 c=color*(.50+.48*l)+vec3(.09)*rim;gl_FragColor=vec4(c,1.);}`));
    gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);position=gl.getAttribLocation(program,'position');normal=gl.getAttribLocation(program,'normal');
    ['target','right','up','front','distance','aspect','color','clipZ'].forEach(n=>uniforms[n]=gl.getUniformLocation(program,n));
    gl.enable(gl.DEPTH_TEST);gl.enableVertexAttribArray(position);gl.enableVertexAttribArray(normal);
    new ResizeObserver(draw).observe(canvas);
    canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();$('#viewer-error').hidden=false;});
    canvas.addEventListener('webglcontextrestored',()=>location.reload());
  }
  function bufferMesh(positions){
    const normals=new Float32Array(positions.length);
    for(let i=0;i<positions.length;i+=9){let ax=positions[i+3]-positions[i],ay=positions[i+4]-positions[i+1],az=positions[i+5]-positions[i+2],bx=positions[i+6]-positions[i],by=positions[i+7]-positions[i+1],bz=positions[i+8]-positions[i+2];let nx=ay*bz-az*by,ny=az*bx-ax*bz,nz=ax*by-ay*bx,l=Math.hypot(nx,ny,nz)||1;for(let k=0;k<3;k++)normals.set([nx/l,ny/l,nz/l],i+k*3);}
    const upload=array=>{const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,array,gl.STATIC_DRAW);return b;};
    return {position:upload(positions),normal:upload(normals),count:positions.length/3};
  }
  function draw(){
    if(!program||!buffers[current])return;
    const dpr=Math.min(window.devicePixelRatio||1,2),w=Math.round(canvas.clientWidth*dpr),h=Math.round(canvas.clientHeight*dpr);
    if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
    gl.viewport(0,0,w,h);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
    const ca=Math.cos(angle),sa=Math.sin(angle),ce=Math.cos(elevation),se=Math.sin(elevation);
    gl.uniform3fv(uniforms.target,target);gl.uniform3fv(uniforms.right,[-sa,ca,0]);gl.uniform3fv(uniforms.up,[-se*ca,-se*sa,ce]);gl.uniform3fv(uniforms.front,[ce*ca,ce*sa,se]);
    gl.uniform1f(uniforms.distance,distance);gl.uniform1f(uniforms.aspect,w/h);gl.uniform3fv(uniforms.color,colors[current]);gl.uniform1f(uniforms.clipZ,+$('#clip').value);
    for(const [key,location] of [['position',position],['normal',normal]]){gl.bindBuffer(gl.ARRAY_BUFFER,buffers[current][key]);gl.vertexAttribPointer(location,3,gl.FLOAT,false,0,0);}
    gl.drawArrays(gl.TRIANGLES,0,buffers[current].count);
  }
  async function selectModel(name){
    const token=++requestId;current=name;
    document.querySelectorAll('[data-model]').forEach(b=>{const active=b.dataset.model===name;b.classList.toggle('selected',active);b.setAttribute('aria-pressed',String(active));});
    $('#model-label').textContent=labels[name];$('#model-meta').textContent='Loading geometry…';
    $('#mesh-download').hidden=!['cut-first','cut-after','transported'].includes(name);$('#mesh-download').href='downloads/'+name+'.obj';
    try{
      if(!buffers[name]){const response=await fetch(models[name].file);if(!response.ok)throw Error('Mesh download failed');buffers[name]=bufferMesh(new Float32Array(await response.arrayBuffer()));}
      if(token!==requestId)return;
      $('#model-meta').textContent=models[name].triangles.toLocaleString()+' triangles · generated 3D mesh';draw();
    }catch(e){$('#model-meta').textContent='Could not load this mesh';$('#viewer-error').hidden=false;console.error(e);}
  }
  function camera(local){detail=local;target=local?[.09,.18,.63]:[.5,.5,.5];distance=local ? .27 : 2.35;angle=-2.40;elevation=local ? .30 : .58;$('#whole').classList.toggle('selected',!local);$('#detail').classList.toggle('selected',local);draw();}
  let drag=null;
  canvas.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointermove',e=>{if(!drag)return;angle-=(e.clientX-drag[0])*.008;elevation=Math.max(-1.4,Math.min(1.4,elevation+(e.clientY-drag[1])*.008));drag=[e.clientX,e.clientY];draw();});
  canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);
  canvas.addEventListener('wheel',e=>{e.preventDefault();distance=Math.max(.055,Math.min(8,distance*Math.exp(e.deltaY*.001)));draw();},{passive:false});
  canvas.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','-','='].includes(e.key))return;e.preventDefault();if(e.key==='ArrowLeft')angle-=.1;if(e.key==='ArrowRight')angle+=.1;if(e.key==='ArrowUp')elevation=Math.min(1.4,elevation+.1);if(e.key==='ArrowDown')elevation=Math.max(-1.4,elevation-.1);if(['+','='].includes(e.key))distance=Math.max(.055,distance*.9);if(e.key==='-')distance=Math.min(8,distance/ .9);draw();});
  document.querySelectorAll('[data-model]').forEach(b=>b.addEventListener('click',()=>selectModel(b.dataset.model)));
  $('#whole').addEventListener('click',()=>camera(false));$('#detail').addEventListener('click',()=>camera(true));$('#reset').addEventListener('click',()=>{$('#clip').value=1.2;camera(detail);});$('#clip').addEventListener('input',draw);
  fetch('models/index.json').then(r=>{if(!r.ok)throw Error('Mesh index failed');return r.json();}).then(data=>{models=data;initialize();return selectModel(current);}).catch(e=>{$('#viewer-error').hidden=false;$('#model-meta').textContent='3D preview unavailable';console.error(e);});

  let sections,localSection=false;
  const NS='http://www.w3.org/2000/svg';
  function el(name,attributes,parent){const node=document.createElementNS(NS,name);for(const[k,v]of Object.entries(attributes))node.setAttribute(k,v);parent.appendChild(node);return node;}
  function sectionDraw(){
    if(!sections)return;const svg=$('#section-svg'),i=+$('#plane').value;svg.replaceChildren();
    const box=localSection?[.025,.22,.14,.26]:[-.025,1.17,-.025,1.12];let [x0,x1,y0,y1]=box;
    const scale=Math.min(880/(x1-x0),440/(y1-y0)),ox=(1000-scale*(x1-x0))/2,oy=(540-scale*(y1-y0))/2;
    const x=v=>ox+(v-x0)*scale,y=v=>540-oy-(v-y0)*scale;
    const defs=el('defs',{},svg),clip=el('clipPath',{id:'plot-clip'},defs);el('rect',{x:ox,y:oy,width:scale*(x1-x0),height:scale*(y1-y0)},clip);
    el('rect',{x:ox,y:oy,width:scale*(x1-x0),height:scale*(y1-y0),fill:'white',stroke:'#e5e5ed'},svg);
    const step=localSection?.05:.25;
    for(let v=Math.ceil(x0/step)*step;v<=x1;v+=step){el('line',{x1:x(v),x2:x(v),y1:oy,y2:540-oy,stroke:'#eeeef3'},svg);el('text',{x:x(v),y:540-oy+23,'text-anchor':'middle'},svg).textContent=v.toFixed(2);}
    for(let v=Math.ceil(y0/step)*step;v<=y1;v+=step){el('line',{x1:ox,x2:1000-ox,y1:y(v),y2:y(v),stroke:'#eeeef3'},svg);el('text',{x:ox-12,y:y(v)+4,'text-anchor':'end'},svg).textContent=v.toFixed(2);}
    const group=el('g',{'clip-path':'url(#plot-clip)'},svg),styles=[['cut_then_deform','#654c95',''],['deform_then_cut','#aa6234',''],['transported_tool_cut','#357486','7 5']];
    for(const [role,color,dash]of styles)for(const loop of sections[role][i].loops){const d=loop.uv.map((p,j)=>(j?'L':'M')+x(p[0]).toFixed(3)+','+y(p[1]).toFixed(3)).join(' ')+'Z';el('path',{d,fill:'none',stroke:color,'stroke-width':1.7,'stroke-dasharray':dash,'vector-effect':'non-scaling-stroke'},group);}
    $('#section-count').textContent='Each: 1 component · 4 holes';
  }
  $('#plane').addEventListener('change',sectionDraw);
  $('#section-whole').addEventListener('click',()=>{localSection=false;$('#section-whole').classList.add('selected');$('#section-detail').classList.remove('selected');sectionDraw();});
  $('#section-detail').addEventListener('click',()=>{localSection=true;$('#section-detail').classList.add('selected');$('#section-whole').classList.remove('selected');sectionDraw();});
  fetch('data/sections.json').then(r=>{if(!r.ok)throw Error('Sections failed');return r.json();}).then(data=>{sections=data;sectionDraw();}).catch(e=>{$('#section-count').textContent='See the section figure for contours';console.error(e);});
})();
