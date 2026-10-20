const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('fs');
(async()=>{
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:390,height:844},colorScheme:'light'});
await page.route('**/*',r=>/cloudflareinsights|google-analytics/.test(r.request().url())?r.abort():r.continue());
await page.goto('http://127.0.0.1:4000/');
await page.keyboard.press('Tab');
const skip=await page.evaluate(()=>document.activeElement.className==='pf-skip');
await page.keyboard.press('Enter');
const skipped=page.url().endsWith('#portfolio-main');
await page.locator('.pf-nav a').filter({hasText:'Research'}).click();
await page.locator('.lang-switch a').click();
await page.waitForLoadState('networkidle');
const translated=page.url().endsWith('/zh/research/');
await page.locator('.theme-toggle').waitFor({state:'visible'});
await page.locator('.theme-toggle').focus();
const before=await page.evaluate(()=>({active:document.activeElement.className,theme:document.documentElement.dataset.theme,system:matchMedia('(prefers-color-scheme:dark)').matches}));
await page.keyboard.press('Enter');
const keyboardTheme=await page.evaluate(()=>document.documentElement.dataset.theme==='dark');
const widths=[];
for(const width of [320,768,1024]){
 await page.setViewportSize({width,height:900});
 for(const route of ['/','/research/','/engineering/','/projects/','/zh/']){
  await page.goto('http://127.0.0.1:4000'+route);
  widths.push({width,route,overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)});
 }
}
const report={skip,skipped,translated,before,keyboardTheme,widths};
fs.writeFileSync(__dirname+'/interaction-check.json',JSON.stringify(report,null,2));
await browser.close();console.log(JSON.stringify(report));
if(!skip||!skipped||!translated||!keyboardTheme||widths.some(w=>w.overflow))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
