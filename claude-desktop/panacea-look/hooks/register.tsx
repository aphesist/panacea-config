import type { Register, ThemeSetArgs } from 'claude-code'

import { makeColors } from './make-colors.js'

// Panacea's "Nothing" palette: pure black, white words, one red. Dark only,
// because the look is about black.
const { theme, problems } = makeColors({
  label: 'Panacea',
  only: 'dark',
  roles: { accent: '#d71921', danger: '#ff4d4d', success: '#4cc38a', warning: '#e6a23c', pro: '#a78bfa' },
  dark: {
    gray: {
      anchors: {
        'surface-0': '#000000',
        'surface-1': '#0b0b0b',
        'surface-2': '#121212',
        'surface-3': '#171717',
        'text-primary': '#ffffff',
        'text-secondary': '#bdbdbd',
        'text-muted': '#8f8f8f',
      },
    },
  },
})

// A faint dot matrix, like the island's dot glyphs, with a soft glow that
// drifts slowly across it. At rest (reduced motion) the glow sits top left.
const SCENE = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice">
<style>
  .glow { animation: drift 90s ease-in-out infinite alternate; }
  .pulse { animation: breathe 14s ease-in-out infinite; }
  @keyframes drift { from { transform: translate(0px, 0px); } to { transform: translate(1100px, 520px); } }
  @keyframes breathe { 0%, 100% { opacity: 0.55; } 50% { opacity: 1; } }
</style>
<defs>
  <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">
    <circle cx="11" cy="11" r="1.3" fill="#ffffff"/>
  </pattern>
  <radialGradient id="soft">
    <stop offset="0" stop-color="#ffffff" stop-opacity="1"/>
    <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
  </radialGradient>
  <mask id="reveal">
    <rect width="1600" height="1000" fill="#1a1a1a"/>
    <g class="glow"><circle cx="300" cy="260" r="420" fill="url(#soft)"/></g>
  </mask>
</defs>
<rect width="1600" height="1000" fill="#000000"/>
<g class="pulse"><rect width="1600" height="1000" fill="url(#dots)" mask="url(#reveal)" opacity="0.10"/></g>
</svg>`

const LOOK: ThemeSetArgs = { colors: theme, backdrop: { scene: 'panacea-dots', glass: false } }

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const unpainted = problems.find(line => line.startsWith("Desktop won't paint"))

    if (unpainted !== undefined) {
      $.ui.toast(unpainted)
    }
    const set = await $.theme.set(LOOK)

    if (!set.isDrawn) {
      $.ui.status(set.reason)
    }

    return next(e)
  })

  on('ui.render', { component: 'Backdrop' }, ($, e, next) => {
    if (e.surface !== 'desktop' && e.surface !== 'mobile') {
      return next(e)
    }
    const { Svg } = $.ui.resolve(e)

    return <Svg source={SCENE} alt="A faint dot matrix with a slow drifting glow" />
  })
}
