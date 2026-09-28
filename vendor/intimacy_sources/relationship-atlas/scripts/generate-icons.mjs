import { readFile } from 'node:fs/promises'
import { chromium } from 'playwright'

const icons = [
  ['public/icon.svg', 'public/icon-192.png', 192],
  ['public/icon.svg', 'public/icon-512.png', 512],
  ['public/icon-maskable.svg', 'public/icon-maskable-512.png', 512],
]

const browser = await chromium.launch({ headless: true })
try {
  for (const [source, target, size] of icons) {
    const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 })
    await page.setContent(await readFile(source, 'utf8'))
    const svg = page.locator('svg')
    await svg.evaluate((element, pixels) => {
      element.style.width = `${pixels}px`
      element.style.height = `${pixels}px`
      element.style.display = 'block'
      document.documentElement.style.background = 'transparent'
      document.body.style.margin = '0'
    }, size)
    await svg.screenshot({ path: target, omitBackground: true })
    await page.close()
  }
} finally {
  await browser.close()
}
