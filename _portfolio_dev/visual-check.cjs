const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('fs');
const path=require('path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const report=[];
 const out=path.join(__dirname,'screenshots');fs.mkdirSync(out,{recursive:true});
 for(const width of [1440,390]){
  const context=await browser.newContext({viewport:{width,height:1000},deviceScaleFactor:1,colorScheme:'light'});
  // Local visual QA must not send telemetry.
  await context.route('**/*',route=> /cloudflareinsights|google-analytics/.test(route.request().url()) ? route.abort() : route.continue());
  const page=await context.newPage();
  for(const lang of ['en','zh'])for(const name of ['home','research','manufacturing','projects']){
   const url='http://127.0.0.1:4000/'+(lang==='zh'?'zh/':'')+(name==='home'?'':name+'/');
   const response=await page.goto(url,{waitUntil:'networkidle'});
   await page.evaluate(async()=>{await document.fonts.ready;for(const im of document.images){if(im.loading==='lazy')im.loading='eager';}await Promise.all([...document.images].map(im=>im.decode().catch(()=>{})));});
   const checks=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,missingImages:[...document.querySelectorAll('.pf-main img')].filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.src),missingAlt:[...document.querySelectorAll('img')].filter(i=>!i.alt).map(i=>i.src),nav:[...document.querySelectorAll('.pf-nav a')].map(a=>a.getAttribute('href')),language:document.querySelector('.lang-switch a')?.getAttribute('href')}));
   report.push({lang,name,width,status:response.status(),...checks});
   await page.screenshot({path:path.join(out,`${lang}-${name}-${width}.png`),fullPage:true});
  }
  await page.goto('http://127.0.0.1:4000/',{waitUntil:'networkidle'});
  await page.locator('.theme-toggle').click();
  const dark=await page.evaluate(()=>({theme:document.documentElement.dataset.theme,background:getComputedStyle(document.body).backgroundColor}));
  await page.screenshot({path:path.join(out,`en-home-dark-${width}.png`),fullPage:true});
  await page.reload({waitUntil:'networkidle'});
  report.push({width,dark,persisted:await page.evaluate(()=>document.documentElement.dataset.theme==='dark')});
  await context.close();
 }
 fs.writeFileSync(path.join(__dirname,'visual-check.json'),JSON.stringify(report,null,2));
 await browser.close();
 console.log(JSON.stringify(report));
 if(report.some(r=>r.overflow||r.missingImages?.length||r.missingAlt?.length||r.status&&r.status!==200||r.persisted===false))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
