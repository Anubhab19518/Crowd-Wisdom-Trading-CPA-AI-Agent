const Apify = require('apify');
const cheerio = require('cheerio');
const got = require('got');

Apify.main(async () => {
    const input = await Apify.getInput() || {};
    const { url, date, selector, api_url } = input;

    if (!url && !api_url) throw new Error('Provide input.url or input.api_url');

    const result = { date: date || new Date().toISOString().slice(0,10), fbx_index: null };

    // If an API URL is provided, try it first (expected to return JSON with fbx_index)
    if (api_url) {
        try {
            const res = await got(api_url, { responseType: 'json', timeout: 30000 });
            const body = res.body;
            if (body && (body.fbx_index || body.fbx)) {
                result.fbx_index = body.fbx_index || body.fbx;
                result.source = api_url;
                await Apify.pushData(result);
                return result;
            }
        } catch (err) {
            console.log('api_url fetch failed, falling back to page scrape', err.message);
        }
    }

    // Use request + cheerio as default (fast) and fall back to puppeteer if needed
    try {
        const r = await got(url, { timeout: 30000 });
        const $ = cheerio.load(r.body);
        let text = '';
        if (selector) {
            const el = $(selector);
            text = el.text();
        } else {
            text = $('body').text();
        }
        const m = text.match(/([0-9]{1,4}(?:\.[0-9]+)?)/);
        if (m) {
            result.fbx_index = parseFloat(m[1]);
            result.source = url;
            await Apify.pushData(result);
            return result;
        }
    } catch (err) {
        console.log('HTTP scrape failed, will try Puppeteer', err.message);
    }

    // Puppeteer fallback
    try {
        const browser = await Apify.launchPuppeteer();
        const page = await browser.newPage();
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 45000 });
        let text = '';
        if (selector) {
            await page.waitForSelector(selector, { timeout: 10000 });
            text = await page.$eval(selector, el => el.textContent || '');
        } else {
            text = await page.evaluate(() => document.body.innerText || '');
        }
        const m = text.match(/([0-9]{1,4}(?:\.[0-9]+)?)/);
        if (m) {
            result.fbx_index = parseFloat(m[1]);
            result.source = url;
        }
        await browser.close();
        await Apify.pushData(result);
        return result;
    } catch (err) {
        console.log('Puppeteer scrape failed', err.message);
    }

    // final fallback
    result.fbx_index = null;
    result.source = 'none';
    await Apify.pushData(result);
    return result;
});
