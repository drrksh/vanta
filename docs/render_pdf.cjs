// Render an HTML file to PDF with headless Chromium.
//   node docs/render_pdf.cjs input.html output.pdf [footer 1|0]
let chromium
try { ({ chromium } = require('playwright')) } catch {
  ({ chromium } = require('/opt/npm-tools/node_modules/playwright'))
}
const path = require('path')

;(async () => {
  const [input, output, footer] = process.argv.slice(2)
  const browser = await chromium.launch()
  const page = await browser.newPage()
  await page.goto('file://' + path.resolve(input), { waitUntil: 'load' })
  await page.evaluate(() => document.fonts.ready)
  const withFooter = footer === '1'
  await page.pdf({
    path: output,
    format: 'A4',
    printBackground: true,
    preferCSSPageSize: true,
    outline: true,
    tagged: true,
    displayHeaderFooter: withFooter,
    headerTemplate: '<span></span>',
    footerTemplate: withFooter
      ? `<div style="width:100%;font-family:Inter,sans-serif;font-size:7.5pt;color:#7a8394;padding:0 17mm;display:flex;justify-content:space-between;">
           <span>VANTA · Technical documentation</span>
           <span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`
      : '<span></span>',
  })
  await browser.close()
})().catch((e) => { console.error(e); process.exit(1) })
