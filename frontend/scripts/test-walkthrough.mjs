import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { transform } from 'esbuild'

const source = await readFile(new URL('../src/walkthrough/timeline.ts', import.meta.url), 'utf8')
const { code } = await transform(source, { loader:'ts', format:'esm' })
const { sampleTimeline, chapters, chapterStart, totalWeight } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`)
const at = (index, local) => sampleTimeline(chapterStart(index) + chapters[index].weight * local / totalWeight)
assert.equal(sampleTimeline(-1).index, 0)
assert.equal(sampleTimeline(2).index, 8)
for (let i = 0; i < chapters.length; i++) assert.equal(at(i, 0.001).index, i)
assert.deepEqual([0.2,0.5,0.8].map(p => at(2,p).scenario), [0,1,2])
assert.equal(at(3,0).calculatorSample,0)
assert.equal(at(3,0.999).calculatorSample,24)
assert.deepEqual([0,1,2,3,4,5,6].map(i => at(4, (i + 0.1) / 7).day), [0,1,2,3,4,5,6])
assert.equal(at(6,0.2).added,false)
assert.equal(at(6,0.8).added,true)
assert.equal(at(1,0.1).query,'')
assert.equal(at(1,0.8).query,'AAPL')
const positions = Array.from({length:1001},(_,i)=>i/1000)
const forward = positions.map(p=>sampleTimeline(p))
const reverse = [...positions].reverse().map(p=>sampleTimeline(p)).reverse()
assert.deepEqual(forward,reverse)
for (const state of forward) {
  assert.ok(state.calculatorSample>=0 && state.calculatorSample<25)
  assert.ok(state.day>=0 && state.day<7)
  assert.ok(Number.isFinite(state.yaw) && Number.isFinite(state.pitch))
}
for(let i=1;i<chapters.length;i++) {
  const before = sampleTimeline(chapterStart(i)-0.0000001)
  const after = sampleTimeline(chapterStart(i)+0.0000001)
  assert.ok(Math.abs(before.yaw-after.yaw)<0.001, `camera yaw discontinuity at ${i}`)
  assert.ok(Math.abs(before.pitch-after.pitch)<0.001, `camera pitch discontinuity at ${i}`)
  for(const key of ['x','y','roll','scale','spread']) assert.ok(Math.abs(before[key]-after[key])<0.001, `${key} discontinuity at ${i}`)
}
// No entrance-only animation or middle/end dead zones. Small scroll increments
// must move the composition in every chapter, not merely increment a progress bar.
for(let chapter=0;chapter<chapters.length;chapter++)for(let step=0;step<99;step++){
  const before=at(chapter,step/100),after=at(chapter,(step+1)/100)
  assert.ok(['x','y','roll','scale','yaw','pitch'].some(key=>Math.abs(before[key]-after[key])>0.0001), `dead zone: chapter ${chapter}, ${step}%`)
}
const page = await readFile(new URL('../src/walkthrough/Preview.tsx',import.meta.url),'utf8')
assert.ok(!/addHolding|saveScenario|fetch\(|localStorage/.test(page),'demo must not perform account writes')
for(const path of ['pages/Login.tsx','pages/Register.tsx','components/GoogleSignInButton.tsx']) {
  const text = await readFile(new URL(`../src/${path}`,import.meta.url),'utf8')
  assert.ok(text.includes("navigate('/valuation/AAPL')"),`wrong auth destination: ${path}`)
}
console.log('PASS: 1,001 reversible states; chapter boundaries; camera continuity; scenarios; 25-sample indices; all 7 dates; simulated watchlist; auth destination wiring.')
