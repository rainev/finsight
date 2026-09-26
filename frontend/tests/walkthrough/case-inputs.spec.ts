import { test, expect } from '@playwright/test'
import fixture from '../fixtures/apple-case-inputs.json' with { type: 'json' }

test('isolated UI: case sliders, draft preservation, precision and reset (all API calls mocked)', async ({page}) => {
  const unexpected:string[]=[]
  const seen:string[]=[]
  await page.route('**/api/**', async route => {
    const request=route.request(), path=new URL(request.url()).pathname
    const headers={'access-control-allow-origin':new URL(process.env.FINSIGHT_TEST_URL || 'http://localhost:4000').origin,'access-control-allow-credentials':'true','access-control-allow-headers':'authorization,content-type','access-control-allow-methods':'GET,POST,OPTIONS'}
    const respond=(data:unknown)=>route.fulfill({json:data,headers})
    if(request.method()==='OPTIONS')return route.fulfill({status:204,headers})
    if(path==='/api/auth/refresh')return respond({access_token:'isolated-fixture-not-a-real-token',user:{id:'fixture-only',email:'fixture@example.test',role:'user'}})
    if(path==='/api/holdings'||path==='/api/valuations')return respond([])
    if(path==='/api/us-valuations')return respond(fixture.list)
    if(path==='/api/us-valuations/AAPL')return respond(fixture.detail)
    if(path==='/api/us-valuations/AAPL/calculator'){
      if(request.method()==='GET')return respond(fixture.calculator)
      const body=request.postDataJSON()
      expect(body.save).not.toBe(true)
      const sample=fixture.calculations.find(result=>result.selected_scenario===body.scenario && Object.entries(body.overrides).every(([key,value])=>Math.abs(result.assumptions[key as keyof typeof result.assumptions]-Number(value))<1e-10))
      if(sample){seen.push(body.scenario);return respond(sample)}
    }
    unexpected.push(`${request.method()} ${path}`)
    return route.abort() // never fall through to authenticated APIs
  })
  await page.goto('/valuation/AAPL')
  await expect(page.getByRole('heading',{name:'Apple Inc.',exact:true})).toBeVisible()
  const growth=page.getByRole('spinbutton',{name:'Initial growth value',exact:true})
  const discount=page.getByRole('spinbutton',{name:'Discount rate value',exact:true})
  const terminal=page.getByRole('spinbutton',{name:'Terminal growth value',exact:true})
  const range=page.getByRole('slider',{name:'Initial growth',exact:true})
  for(const [name,values,price,exactGrowth] of [
    ['Bear',['6.17','10.12','1.50'],'$79.80',.06166084576940628],
    ['Base',['8.17','9.12','2.00'],'$103.33',.08166084576940628],
    ['Bull',['9.67','8.62','2.30'],'$123.16',.09666084576940628],
  ] as const){
    await page.getByRole('button',{name:new RegExp(`^${name} case`,'i')}).click()
    await expect(growth).toHaveValue(values[0]);await expect(discount).toHaveValue(values[1]);await expect(terminal).toHaveValue(values[2])
    expect(Number(await range.inputValue())).toBeCloseTo(exactGrowth,12)
    await expect(page.locator('.intrinsic-hero>strong')).toHaveText(price)
    await page.waitForTimeout(350)
  }
  await growth.fill('11');await growth.blur()
  const edited=fixture.calculations.find(row=>row.selected_scenario==='high'&&row.assumptions.initial_growth===.11)!
  await expect(page.locator('.intrinsic-hero>strong')).toHaveText(new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(edited.result.high))
  await page.getByRole('button',{name:/^Base case/i}).click()
  await expect(growth).toHaveValue('8.17')
  await page.getByRole('button',{name:/^Bull case/i}).click()
  await expect(growth).toHaveValue('11.00')
  await range.focus();await page.keyboard.press('ArrowRight')
  await expect(growth).toHaveValue('11.50')
  await page.getByRole('button',{name:'Reset',exact:true}).click()
  await expect(growth).toHaveValue('9.67')
  await expect(page.locator('.intrinsic-hero>strong')).toHaveText('$123.16')
  expect(unexpected).toEqual([])
  expect(seen).toEqual(expect.arrayContaining(['low','base','high']))
  await page.screenshot({path:'../docs/audit/evidence/walkthrough/case-inputs-isolated.png'})
})
