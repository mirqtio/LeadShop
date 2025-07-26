# PageSpeed API Data Elements Summary

## Top-Level Structure

### Mobile Result
- **url**: "https://www.google.com"
- **strategy**: "mobile"
- **analysis_timestamp**: ISO timestamp
- **analysis_duration_ms**: Time taken for analysis
- **cost_cents**: 0.25 (API call cost)

### Core Web Vitals (Extracted Metrics)
- **first_contentful_paint**: 1981ms
- **largest_contentful_paint**: 6460ms
- **cumulative_layout_shift**: 0.0
- **total_blocking_time**: 227ms
- **time_to_interactive**: 6468ms
- **performance_score**: 71/100

### Lighthouse Result (Raw Data)
- **requestedUrl**: Original URL requested
- **finalUrl**: Final URL after redirects
- **mainDocumentUrl**: Main document URL
- **finalDisplayedUrl**: URL displayed to user
- **lighthouseVersion**: "12.8.0"
- **userAgent**: Browser user agent used
- **fetchTime**: ISO timestamp of analysis
- **environment**: Test environment details
  - networkUserAgent: Mobile emulation user agent
  - hostUserAgent: Actual Chrome user agent
  - benchmarkIndex: Performance benchmark score
  - credits: Tool versions (e.g., axe-core)

### Configuration Settings
- **emulatedFormFactor**: "mobile"
- **formFactor**: "mobile"
- **locale**: "en-US"
- **onlyCategories**: ["performance", "accessibility", "best-practices", "seo"]
- **channel**: "lr"

### Audits (Large Dictionary)
Contains detailed audit results for various metrics including:
- meta-viewport
- forced-reflow-insight
- focusable-controls
- And many more performance/accessibility/SEO audits

### Categories (Performance Scores)
Not shown in detail but includes:
- Performance category score
- Accessibility category score
- Best practices category score
- SEO category score

### Category Groups
Defines groupings for audit results:
- **best-practices-general**: General best practices
- **a11y-audio-video**: Audio/video accessibility
- **a11y-navigation**: Navigation accessibility
- **metrics**: Performance metrics
- **best-practices-trust-safety**: Trust and safety
- **seo-content**: SEO content best practices
- **seo-mobile**: Mobile friendliness
- **best-practices-browser-compat**: Browser compatibility
- **a11y-best-practices**: Accessibility best practices
- **a11y-tables-lists**: Tables/lists accessibility
- **a11y-language**: Internationalization
- **best-practices-ux**: User experience
- **a11y-aria**: ARIA usage
- **a11y-color-contrast**: Color contrast
- **a11y-names-labels**: Names and labels
- **insights**: Performance insights
- **seo-crawl**: Crawling and indexing
- **diagnostics**: Performance diagnostics

### Timing
- **total**: 14607ms (total Lighthouse runtime)

### i18n (Internationalization)
Contains all the user-facing strings used in the Lighthouse report

### Entities
List of third-party entities detected on the page

### Full Page Screenshot
- **screenshot.data**: Base64-encoded WebP image of the full page
- **screenshot.height**: 858px
- **screenshot.width**: 412px
- **nodes**: Dictionary mapping element IDs to their positions/dimensions

### Desktop Result
Similar structure to mobile but with:
- **strategy**: "desktop"
- Different performance metrics (usually better)
- Different viewport dimensions
- Different user agent strings

## Summary of 53 Decomposed Metrics

Based on the requirements, these metrics should be extracted and stored:

### PageSpeed (7 metrics)
1. First Contentful Paint (FCP) - ✓ Available
2. Largest Contentful Paint (LCP) - ✓ Available  
3. Cumulative Layout Shift (CLS) - ✓ Available
4. Total Blocking Time (TBT) - ✓ Available
5. Time to Interactive (TTI) - ✓ Available
6. Speed Index - Not in core_web_vitals, but available in audits
7. Performance Score - ✓ Available

### Additional Data Available
- Detailed audit results for each metric
- Opportunities for improvement
- Diagnostics information
- Accessibility scores
- SEO scores
- Best practices scores
- Full page screenshots
- Element positioning data
- Third-party resource analysis
- Network request information