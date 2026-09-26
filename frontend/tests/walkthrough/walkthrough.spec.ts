import { test, expect, type Page } from '@playwright/test'
import { writeFile } from 'node:fs/promises'

const chapterNames = ['Introduction','Discovery','Scenarios','Assumptions','News','Evidence','Portfolio','AI Insights','FinSight']
const ids = ['intro','discover','scenarios','assumptions','news','evidence','portfolio','insights','continue']
async function position(page: Page, id: string, fraction: number) {
  const target = await page.locator(`#${id}`).evaluate((element, p) => {
    const rect = element.getBoundingClientRect()
    return rect.top + window.scrollY - (innerWidth <= 760 ? 68 : 80) + rect.height * p
  },fraction)
  const current = await page.evaluate(()=>scrollY)
  await page.mouse.move(300,300)
  await page.mouse.wheel(0,target-current)
  await expect.poll(async()=>Math.abs(await page.evaluate(()=>scrollY)-target)).toBeLessThan(1.1)
  await expect(page.locator('.wt')).toHaveAttribute('data-active-chapter',id)
  await expect.poll(()=>page.evaluate(()=>Number((document.querySelector('.wt') as HTMLElement).dataset.renderedScroll) === scrollY)).toBe(true)
}

test('native forward/backward scroll keeps every scenario, calculator sample and news date paired',async({page})=>{
  const writes:string[]=[]
  const errors:string[]=[]
  page.on('request',request=>{if(/holdings|saved-runs|research\/runs/.test(request.url()) && request.method()!=='GET')writes.push(request.url())})
  page.on('pageerror',error=>errors.push(error.message))
  await page.goto('/')
  await expect(page.locator('.wt')).toHaveAttribute('data-mode','cinematic')
  for(const [fraction,name,value,left] of [[0.2,'bear','$79.80','0%'],[0.5,'base','$103.33','54.2629%'],[0.85,'bull','$123.16','100%']] as const) {
    await position(page,'scenarios',fraction)
    await expect(page.locator('.wt-stage .wt-scenario')).toHaveAttribute('data-scenario',name)
    await expect(page.locator('.wt-stage .wt-value')).toHaveText(value)
    await expect(page.locator('.wt-stage .wt-gauge-marker')).toHaveCSS('left',/px/)
    expect(await page.locator('.wt-stage .wt-gauge-marker').evaluate(e=>(e as HTMLElement).style.left)).toBe(left)
  }
  await position(page,'assumptions',0.001)
  await expect(page.locator('.wt-stage output').first()).toHaveText('8.17%')
  await expect(page.locator('.wt-stage .wt-calculation>strong')).toHaveText('$103.33')
  await position(page,'assumptions',0.999)
  await expect(page.locator('.wt-stage output').first()).toHaveText('12.00%')
  await expect(page.locator('.wt-stage .wt-calculation>strong')).toHaveText('$112.32')
  const titles=['Apple Maps advertising','Apple opens a manufacturing','Report: lower display','Two puzzle games','Apple previews immersive','A quiet page','A quiet page']
  for(let i=0;i<7;i++){
    await position(page,'news',(i+0.2)/7)
    await expect(page.locator('.wt-stage .wt-news-date')).toHaveText(`August ${14-i}, 2026`)
    await expect(page.locator('.wt-stage .wt-news-story h3')).toContainText(titles[i])
    await expect(page.locator('.wt-stage .wt-days .is-selected strong')).toHaveText(String(14-i))
  }
  await position(page,'portfolio',0.85)
  await expect(page.locator('.wt-stage .wt-demo-action')).toHaveText('Apple added to watchlist')
  await position(page,'portfolio',0.1)
  await expect(page.locator('.wt-stage .wt-demo-action')).toHaveText('Add Apple to watchlist')
  await position(page,'assumptions',0.001)
  await expect(page.locator('.wt-stage output').first()).toHaveText('8.17%')
  await position(page,'scenarios',0.5)
  await expect(page.locator('.wt-stage .wt-value')).toHaveText('$103.33')
  expect(writes).toEqual([])
  expect(errors).toEqual([])
  await page.screenshot({path:'../docs/audit/evidence/walkthrough/desktop-scenarios.png'})
})

test('chapter jumps, keyboard finale, browser back, idle rendering and signed-out entry',async({page})=>{
  await page.goto('/')
  await expect(page.locator('.wt')).toHaveAttribute('data-mode','cinematic')
  for(const i of [8,1,5,3,7,0,6,4,2,8]) {
    await page.getByRole('link',{name:`${i+1}. ${chapterNames[i]}`,exact:true}).click()
    await expect(page.locator('.wt')).toHaveAttribute('data-active-chapter',ids[i])
  }
  await position(page,'continue',0.3)
  const renders = await page.locator('canvas').getAttribute('data-renders')
  await page.waitForTimeout(400)
  expect(await page.locator('canvas').getAttribute('data-renders')).toBe(renders)
  await page.screenshot({path:'../docs/audit/evidence/walkthrough/desktop-finale.png'})
  const cta = page.getByRole('link',{name:'Continue to FinSight',exact:true})
  await cta.focus(); await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading',{name:'Sign in',exact:true})).toBeVisible()
  await page.goBack()
  await expect(page.locator('.wt')).toBeVisible()
  await page.keyboard.press('Control+Home')
  await page.getByRole('link',{name:'Skip to final invitation',exact:true}).focus()
  await page.keyboard.press('Enter')
  await expect(cta).toBeVisible()
})

for(const mode of ['reduced','unavailable','lost'] as const) test(`${mode} keeps a complete usable static walkthrough`,async({page})=>{
  if(mode==='reduced')await page.emulateMedia({reducedMotion:'reduce'})
  if(mode==='unavailable')await page.addInitScript(()=>{
    const original=HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext=function(kind:string,...args:unknown[]){
      if(kind==='webgl'||kind==='webgl2'||kind==='experimental-webgl')return null
      return original.apply(this,[kind,...args] as never)
    } as typeof original
  })
  await page.goto('/')
  if(mode==='lost'){
    await expect(page.locator('.wt')).toHaveAttribute('data-mode','cinematic')
    await page.locator('canvas').evaluate(canvas=>(canvas as HTMLCanvasElement).getContext('webgl2')?.getExtension('WEBGL_lose_context')?.loseContext())
  }
  await expect(page.locator('.wt')).toHaveAttribute('data-mode','static')
  await expect(page.locator('.wt-static-preview')).toHaveCount(9)
  await expect(page.locator('.wt-static-news details')).toHaveCount(7)
  await page.locator('.wt-static-news summary').last().click()
  await expect(page.locator('.wt-static-news details').last()).toContainText('This does not mean no news occurred')
  await page.getByRole('link',{name:'9. FinSight',exact:true}).click()
  await expect(page.getByRole('link',{name:'Continue to FinSight',exact:true})).toBeInViewport()
  await expect(page.locator('canvas')).not.toBeVisible()
  await page.screenshot({path:`../docs/audit/evidence/walkthrough/${mode}-fallback.png`})
})

for(const viewport of [{width:390,height:844},{width:768,height:1024}])test(`responsive ${viewport.width} and UI bounds`,async({page})=>{
  await page.setViewportSize(viewport)
  await page.goto('/')
  await expect(page.locator('.wt')).toHaveAttribute('data-mode','cinematic')
  for(const i of [0,3,4,5,8]){
    await page.getByRole('link',{name:`${i+1}. ${chapterNames[i]}`,exact:true}).click()
    await expect(page.locator('.wt')).toHaveAttribute('data-active-chapter',ids[i])
    const bounds=await page.evaluate(()=>{
      const frame=document.querySelector('.wt-stage-panel')!.getBoundingClientRect()
      const copy=document.querySelector('.wt-chapter.is-active .wt-copy')!.getBoundingClientRect()
      return {width:document.documentElement.scrollWidth,viewport:innerWidth,frame:{top:frame.top,bottom:frame.bottom,right:frame.right,left:frame.left},copy:{top:copy.top,bottom:copy.bottom}}
    })
    expect(bounds.width).toBeLessThanOrEqual(bounds.viewport)
    expect(bounds.frame.left).toBeGreaterThanOrEqual(0)
    expect(bounds.frame.right).toBeLessThanOrEqual(viewport.width)
    if(viewport.width<760){
      expect(bounds.copy.top).toBeGreaterThanOrEqual(bounds.frame.bottom-2)
      expect(bounds.copy.bottom).toBeLessThan(viewport.height-35)
    }
  }
  expect(Number(await page.locator('canvas').getAttribute('data-dpr'))).toBeLessThanOrEqual(viewport.width<760?1:1.5)
  await page.screenshot({path:`../docs/audit/evidence/walkthrough/${viewport.width}-finale.png`})
})

test('measure scroll frame cadence on this device and exercise simple-view switching',async({page})=>{
  await page.goto('/')
  await expect(page.locator('.wt')).toHaveAttribute('data-mode','cinematic')
  await position(page,'scenarios',0.1)
  const collection=page.evaluate(()=>new Promise<{intervals:number[]; renderMs:number[]}>(resolve=>{
    const intervals:number[]=[],renderMs:number[]=[]
    let previous=0, count=0
    const frame=(time:number)=>{
      if(previous && count>10) {
        intervals.push(time-previous)
        renderMs.push(Number((document.querySelector('canvas') as HTMLCanvasElement).dataset.renderMs))
      }
      previous=time
      if(++count<100) requestAnimationFrame(frame)
      else resolve({intervals,renderMs})
    }
    requestAnimationFrame(frame)
  }))
  for(let i=0;i<38;i++){await page.mouse.wheel(0,25);await page.waitForTimeout(20)}
  const samples=await collection
  const sorted=[...samples.intervals].sort((a,b)=>a-b)
  const cpu=[...samples.renderMs].sort((a,b)=>a-b)
  const renderer=await page.locator('canvas').evaluate(canvas=>{
    const gl=(canvas as HTMLCanvasElement).getContext('webgl2')!
    const info=gl.getExtension('WEBGL_debug_renderer_info')
    return info ? String(gl.getParameter(info.UNMASKED_RENDERER_WEBGL)) : 'Not exposed by browser'
  })
  const metrics={
    environment:'Isolated local Chrome; 1440×1000, DPR 1. Not a universal/device-independent performance guarantee.',
    renderer,
    samples:sorted.length,
    medianFrameMs:sorted[Math.floor(sorted.length/2)],
    p95FrameMs:sorted[Math.floor(sorted.length*.95)],
    maxFrameMs:Math.max(...sorted),
    framesOver34ms:sorted.filter(n=>n>34).length,
    medianRendererSubmissionMs:cpu[Math.floor(cpu.length/2)],
    p95RendererSubmissionMs:cpu[Math.floor(cpu.length*.95)],
  }
  console.log('Measured scroll performance:',JSON.stringify(metrics))
  await writeFile('../docs/audit/evidence/walkthrough/performance.json',JSON.stringify(metrics,null,2)+'\n')
  await page.getByRole('button',{name:'Simple view',exact:true}).click()
  await expect(page.locator('.wt')).toHaveAttribute('data-mode','static')
  await page.getByRole('button',{name:'Cinematic view',exact:true}).click()
  await expect(page.locator('.wt')).toHaveAttribute('data-mode','cinematic')
})

test('short phones and landscape windows use the readable stacked presentation',async({page})=>{
  await page.setViewportSize({width:375,height:667})
  await page.goto('/')
  await expect(page.locator('.wt')).toHaveAttribute('data-mode','static')
  await expect(page.getByRole('button',{name:'Compact view',exact:true})).toBeDisabled()
  await page.getByRole('link',{name:'9. FinSight',exact:true}).click()
  await expect(page.getByRole('link',{name:'Continue to FinSight',exact:true})).toBeInViewport()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(375)
})

test('small scrolls move actual UI pieces throughout every shorter chapter',async({page})=>{
  await page.goto('/')
  await expect(page.locator('.wt')).toHaveAttribute('data-mode','cinematic')
  const distance=await page.evaluate(()=>document.documentElement.scrollHeight-innerHeight)
  expect(distance).toBeLessThan(5100) // old desktop tour was about 9,300px at this viewport
  const selectors=['.wt-case','.wt-search','.wt-case','.wt-assumption','.wt-news-story','.wt-source','.wt-watchlist','.wt-ai-icon','.wt-final-grid>div']
  const observations=[]
  for(let chapter=0;chapter<ids.length;chapter++)for(const fraction of [0.05,0.45,0.85]){
    // The finale has physical sticky-stage runway after its nominal animation span.
    const unit=await page.locator('#intro').evaluate(e=>e.getBoundingClientRect().height)
    const height=await page.locator(`#${ids[chapter]}`).evaluate(e=>e.getBoundingClientRect().height)
    const local=chapter===8?fraction*unit/height:fraction
    await position(page,ids[chapter],local)
    const piece=page.locator(`.wt-stage ${selectors[chapter]}`).first()
    const before=await piece.evaluate(e=>({panel:getComputedStyle(document.querySelector('.wt-stage-panel')!).transform,piece:getComputedStyle(e).transform,scroll:scrollY}))
    await page.mouse.wheel(0,12)
    await expect.poll(()=>piece.evaluate(e=>getComputedStyle(e).transform)).not.toBe(before.piece)
    await expect.poll(()=>page.locator('.wt-stage-panel').evaluate(e=>getComputedStyle(e).transform),`${ids[chapter]} at ${fraction}: camera moves`).not.toBe(before.panel)
    observations.push({chapter:ids[chapter],fraction,moved:true})
    await page.mouse.wheel(0,-12)
    await expect.poll(()=>piece.evaluate(e=>getComputedStyle(e).transform)).toBe(before.piece)
  }
  await writeFile('../docs/audit/evidence/walkthrough/continuous-motion.json',JSON.stringify({desktopScrollDistance:distance,incrementPx:12,observations},null,2)+'\n')
  await position(page,'intro',0.05)
  await page.screenshot({path:'../docs/audit/evidence/walkthrough/continuous-before.png'})
  await position(page,'intro',0.7)
  await page.screenshot({path:'../docs/audit/evidence/walkthrough/continuous-after.png'})
})
