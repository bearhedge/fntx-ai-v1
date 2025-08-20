# FNTX Trading Terminal - Cyberpunk Theme Variations

## Theme System Architecture

Each theme is designed to be toggleable via Settings (Screen 18) with sub-100ms switching time. All themes maintain core functionality while enhancing visual aesthetics.

---

## 1. MATRIX RAIN THEME

### Color Palette
```
Background:     #000000 (Pure Black)
Primary Text:   #00FF41 (Matrix Green)
Accent:         #00CC33 (Darker Green)
Profit:         #39FF14 (Neon Green)
Loss:           #FF1744 (Digital Red)
Borders:        #00FF41 (Matrix Green)
Rain Effect:    #008F11 (Background Green)
```

### ASCII Art Enhancements
- Falling katakana/numbers in empty spaces (non-blocking)
- Digital rain columns update every 500ms
- Glowing cursor with phosphor trail effect
- Binary patterns in loading screens

### Special Effects
- **Rain Generator**: Background process updates 5-10 columns per cycle
- **Phosphor Decay**: Text briefly glows brighter on update
- **Code Waterfall**: Loading screens show cascading binary
- **Wake Effect**: Rain parts around active windows

### Main Dashboard Example

```
╔══════════════════════════════════════════════════════════════════════════════╗
║ ｱ  2  ﾈ  FNTX TRADING TERMINAL v2.0 │ MATRIX RAIN  ｷ  9  ﾂ  ║
║ 1  ｿ  8  └─ Connecting to the Grid...  5  ﾏ  3  ｦ  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌─[ PORTFOLIO OVERVIEW ]────────────────────────┐  0  1  0  1            ║
║  │                                                │  1  0  1  0            ║
║  │  Account: FN-7X9K2  ░▒▓█ CONNECTED █▓▒░      │  ﾈ  ｷ  ﾂ  ﾏ            ║
║  │  Balance: $127,439.82  ▲ +2.34%               │                        ║
║  │  P&L Today: +$2,891.23 ████████░░            │  0  1  1  0            ║
║  │                                                │  1  0  0  1            ║
║  └────────────────────────────────────────────────┘  ｱ  ｿ  ﾗ  ﾜ            ║
║                                                                              ║
║  ┌─[ ACTIVE POSITIONS ]───────────────────────────────────────────┐        ║
║  │  > SPY 450C 12/15  │  +$1,234  │  ▲ +5.67%  │  DELTA: 0.65   │  0  1  ║
║  │  > QQQ 380P 12/20  │  -$567    │  ▼ -2.34%  │  DELTA: -0.42  │  1  0  ║
║  │  > TSLA 240C 01/15 │  +$3,456  │  ▲ +12.3%  │  DELTA: 0.78   │  ﾂ  ﾏ  ║
║  └──────────────────────────────────────────────────────────────────┘        ║
║                                                                              ║
║  [F1] Orders  [F2] Greeks  [F3] Chain  [F4] Scanner  [ESC] Exit  1  0  1  ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Performance Impact
- **CPU**: +2-3% for rain animation
- **Memory**: +5MB for effect buffers
- **Latency**: <10ms per frame update
- **Optimization**: Rain updates only visible columns

### UX Considerations
- Rain opacity reduced in data-heavy areas
- Toggleable rain intensity (Light/Medium/Heavy)
- Rain pauses during critical operations
- High contrast mode available for accessibility

---

## 2. HONG KONG NEON THEME

### Color Palette
```
Background:     #0A0014 (Deep Purple-Black)
Primary:        #FF006E (Neon Pink)
Secondary:      #00F5FF (Cyan)
Profit:         #00FF88 (Mint Green)
Loss:           #FF3366 (Hot Pink)
Borders:        #8B00FF (Purple)
Glow:           #FF00FF (Magenta)
Accent:         #FFFF00 (Neon Yellow)
```

### ASCII Art Enhancements
- Decorative CJK characters: 香港 金融 期權 交易
- Neon sign borders with glow effects
- Vertical text for section dividers
- Holographic panel effects

### Special Effects
- **Neon Pulse**: Borders pulse with soft glow
- **Holo-Shimmer**: Active panels have iridescent effect
- **Kanji Decorators**: Contextual Japanese/Chinese characters
- **Cybercity Background**: Subtle skyline ASCII art

### Main Dashboard Example

```
╔═══━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━═══╗
║░▒▓█ 香港金融終端 FNTX TRADING █▓▒░ ネオン東京 2089 ║
╠═══━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━═══╣
║                                                                              ║
║  ╭─〔 資産概要 PORTFOLIO 〕─────────────────────╮                          ║
║  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │  期                      ║
║  │  Account: FN-7X9K2  ●━━━● ONLINE           │  權                      ║
║  │  Balance: ¥127,439,820  ↗ +2.34%           │  交                      ║
║  │  今日 P&L: +¥289,123 ▰▰▰▰▰▰▰▰▱▱           │  易                      ║
║  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │                          ║
║  ╰────────────────────────────────────────────────╯                          ║
║                                                                              ║
║  ╭─〔 活躍部位 POSITIONS 〕──────────────────────────────────────────╮      ║
║  │  ▶ SPY 450C 12/15  │  +¥123,400  │  ↗ +5.67%  │  Δ: 0.65        │      ║
║  │  ▶ QQQ 380P 12/20  │  -¥56,700   │  ↘ -2.34%  │  Δ: -0.42       │      ║
║  │  ▶ TSLA 240C 01/15 │  +¥345,600  │  ↗ +12.3%  │  Δ: 0.78        │      ║
║  ╰───────────────────────────────────────────────────────────────────╯      ║
║                                                                              ║
║  〔F1〕注文 〔F2〕希臘 〔F3〕連鎖 〔F4〕掃描 〔ESC〕出口                   ║
╚═══━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━═══╝
```

### Performance Impact
- **CPU**: +1-2% for glow effects
- **Memory**: +3MB for glow buffers
- **Latency**: <5ms per update
- **Optimization**: Glow computed only on state change

### UX Considerations
- CJK characters are decorative only
- English primary for all functional text
- Adjustable neon intensity
- Color-blind friendly mode available

---

## 3. GLITCH ART THEME

### Color Palette
```
Background:     #0D0D0D (Dark Gray)
Primary:        #FFFFFF (White)
Glitch1:        #FF0090 (Magenta)
Glitch2:        #00FFFF (Cyan)
Glitch3:        #FFFF00 (Yellow)
Profit:         #00FF00 (Green)
Loss:           #FF0000 (Red)
Corruption:     #FF00FF (Purple)
```

### ASCII Art Enhancements
- Intentional character corruption in decorative areas
- RGB channel separation effects
- Datamosh patterns for transitions
- Binary noise in empty spaces

### Special Effects
- **Glitch Burst**: Random 50ms glitches on updates
- **Channel Shift**: RGB separation on hover
- **Data Corruption**: Visual artifacts (non-functional)
- **Scan Lines**: Horizontal interference patterns

### Main Dashboard Example

```
╔═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╦═╗
║▓░F░N░T░X░ ░T░R░▓░D░I░N░G░ ░T░E░R░M░I░N░▓░L░ ░v░2░.░0░ ░[░G░L░I░T░C░H░]░▓║
╠═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╩═╣
║                                                                              ║
║  ┌┬┬[ P0RTF0L10_0V3RV13W ]┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┐  ░▒▓█▓▒░                ║
║  ├┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┤  ▓▒░█░▒▓                ║
║  │  Ac©ount: FN-7X9K2  ◉◉◉ C0NN3CT3D ◉◉◉      │  ░▓▒█▒▓░                ║
║  │  B▲lance: $127,4▓9.82  ▲ +2.3█%             │                          ║
║  │  P&█ Today: +$2,89▓.23 ██▓█▓██░░            │  01001110                ║
║  │  ░▒▓█████████████████████████████████▓▒░    │  10110001                ║
║  └┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┘  11010110                ║
║                                                      00101101                ║
║  ┌┬[ ▲CT1V3_P0S1T10NS ]┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┬┐    ║
║  │  > SPY 45█C 12/15  │  +$1,2▓4  │  ▲ +5.█7%  │  D3LT▲: 0.65      │    ║
║  │  > QQQ 38█P 12/20  │  -$5█7    │  ▼ -2.▓4%  │  D3LT▲: -0.42     │    ║
║  │  > TSL▲ 240C 01/15 │  +$3,█56  │  ▲ +12.█%  │  D3LT▲: 0.78      │    ║
║  └┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┘    ║
║                                                                              ║
║  [F1]_0rd3rs  [F2]_Gr33ks  [F3]_Ch▲1n  [F4]_Sc▲nn3r  [ESC]_3x1t  ▓░▒█▒░▓  ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Performance Impact
- **CPU**: +3-4% for glitch processing
- **Memory**: +4MB for corruption buffers
- **Latency**: <15ms for glitch effects
- **Optimization**: Glitches pre-computed and cached

### UX Considerations
- Glitches never affect actual data values
- Intensity adjustable (Subtle/Medium/Intense)
- Can disable during critical operations
- Clear mode for accessibility

---

## 4. MINIMALIST CYBER THEME

### Color Palette
```
Background:     #000000 (Pure Black)
Primary:        #E0E0E0 (Light Gray)
Accent:         #00D4FF (Electric Blue)
Profit:         #00FF9F (Mint)
Loss:           #FF0055 (Crimson)
Borders:        #404040 (Dark Gray)
Highlight:      #FFFFFF (White)
```

### ASCII Art Enhancements
- Circuit pattern borders: ─═╪╫╬═─
- Minimalist node connectors
- Clean geometric dividers
- Subtle tech patterns

### Special Effects
- **Circuit Trace**: Animated current flow in borders
- **Node Pulse**: Connection points pulse softly
- **Data Stream**: Subtle flow indicators
- **Grid Overlay**: Optional alignment grid

### Main Dashboard Example

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ FNTX://TERMINAL.v2.0                                         [CYBER.MINIMAL] │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ╭─────────────────────────────────────────╮                               │
│  │ PORTFOLIO::OVERVIEW                      │                               │
│  ├─────────────────────────────────────────┤                               │
│  │ Account ID: FN-7X9K2     ● CONNECTED    │                               │
│  │ Balance: $127,439.82     ↑ +2.34%       │                               │
│  │ P&L Today: +$2,891.23    ▪▪▪▪▪▪▪▪──     │                               │
│  ╰─────────────────────────────────────────╯                               │
│                                                                              │
│  ╭─────────────────────────────────────────────────────────────────╮       │
│  │ POSITIONS::ACTIVE                                               │       │
│  ├─────────────────────────────────────────────────────────────────┤       │
│  │ • SPY 450C 12/15  │ +$1,234 │ ↑ +5.67% │ Δ: 0.65              │       │
│  │ • QQQ 380P 12/20  │ -$567   │ ↓ -2.34% │ Δ: -0.42             │       │
│  │ • TSLA 240C 01/15 │ +$3,456 │ ↑ +12.3% │ Δ: 0.78              │       │
│  ╰─────────────────────────────────────────────────────────────────╯       │
│                                                                              │
│  F1::Orders  F2::Greeks  F3::Chain  F4::Scanner  ESC::Exit                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Performance Impact
- **CPU**: +0.5% minimal overhead
- **Memory**: +1MB for patterns
- **Latency**: <2ms per update
- **Optimization**: Static elements cached

### UX Considerations
- Maximum readability focus
- Clean, distraction-free interface
- Subtle animations only
- Perfect for extended trading sessions

---

## 5. VINTAGE TERMINAL THEME

### Color Palette
```
Background:     #000000 (CRT Black)
Primary:        #FFAA00 (Amber)
Alt Primary:    #00FF00 (P1 Phosphor Green)
Highlight:      #FFFF00 (Bright Amber)
Profit:         #00FF00 (Green)
Loss:           #FF8800 (Orange-Red)
Scanlines:      #111111 (Faint)
Phosphor Glow:  #FFCC00 (Amber Glow)
```

### ASCII Art Enhancements
- CRT screen curvature simulation
- Scanline overlays
- Phosphor burn-in effects
- Retro ASCII art logos

### Special Effects
- **CRT Curvature**: Slight text warping at edges
- **Scanlines**: Horizontal scan pattern
- **Phosphor Persistence**: Ghosting on updates
- **Flicker**: Occasional authentic CRT flicker
- **Burn-in**: Subtle permanent elements

### Main Dashboard Example

```
  ╔════════════════════════════════════════════════════════════════════════╗
 ╱                                                                          ╲
│  ▄▄▄▄▄ ▄   ▄ ▄▄▄▄▄ ▄   ▄    TRADING SYSTEM v2.0                          │
│  █     ██  █   █   ▀▄ ▄▀    Build 2089.12.15                             │
│  ████  █ ▀▄█   █    ▄▀▄     Amber Phosphor Mode                          │
│  █     █   █   █   ▄▀ ▀▄                                                 │
│  █     █   █   █   ▀   ▀    ════════════════════════════════════════     │
├────────────────────────────────────────────────────────────────────────────┤
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│                                                                            │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓                              │
│  ┃ SYSTEM STATUS: PORTFOLIO OVERVIEW      ┃                              │
│ ─┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│  ┃ ACCT: FN-7X9K2     [●] ONLINE          ┃                              │
│  ┃ BAL:  $127,439.82  [↑] +2.34%          ┃                              │
│ ─┃ P&L:  +$2,891.23   ████████░░          ┃─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛                              │
│                                                                            │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓        │
│ ─┃ ACTIVE POSITIONS                                            ┃─ ─ ─ ─ │
│  ┃ > SPY 450C 12/15  : +$1,234 : [↑] +5.67% : DELTA: 0.65    ┃        │
│  ┃ > QQQ 380P 12/20  : -$567   : [↓] -2.34% : DELTA: -0.42   ┃        │
│ ─┃ > TSLA 240C 01/15 : +$3,456 : [↑] +12.3% : DELTA: 0.78    ┃─ ─ ─ ─ │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛        │
│                                                                            │
│  <F1> ORDERS  <F2> GREEKS  <F3> CHAIN  <F4> SCANNER  <ESC> LOGOFF       │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
 ╲                                                                          ╱
  ╚════════════════════════════════════════════════════════════════════════╝
```

### Performance Impact
- **CPU**: +2% for CRT effects
- **Memory**: +2MB for effect buffers
- **Latency**: <8ms per frame
- **Optimization**: Scanlines rendered once

### UX Considerations
- Toggle between Amber/Green phosphor
- Adjustable CRT effects intensity
- Modern mode for extended use
- Nostalgia without sacrificing function

---

## Implementation Guidelines

### Theme Switching Architecture
```python
class ThemeManager:
    def __init__(self):
        self.themes = {
            'baseline': BaselineTheme(),
            'matrix': MatrixRainTheme(),
            'neon': HongKongNeonTheme(),
            'glitch': GlitchArtTheme(),
            'cyber': MinimalistCyberTheme(),
            'vintage': VintageTerminalTheme()
        }
        self.current = 'baseline'
    
    def switch_theme(self, theme_name):
        # Sub-100ms theme switch
        self.cleanup_current()
        self.current = theme_name
        self.apply_theme()
```

### Performance Optimization
- Pre-compute all static effects
- Use dirty-rectangle updates
- Cache frequently used patterns
- Implement effect LOD (Level of Detail)
- Background thread for non-critical animations

### Accessibility Features
- High contrast mode for each theme
- Disable animations option
- Colorblind friendly palettes
- Screen reader compatibility mode
- Reduced motion settings

### Storage Requirements
- Base theme: ~500KB
- Per theme: ~200KB additional
- Effect cache: ~5MB max
- Total: <10MB for all themes

### User Preferences
```yaml
theme_preferences:
  current_theme: "matrix"
  animation_level: "medium"  # off, low, medium, high
  effect_intensity: 0.7      # 0.0 to 1.0
  phosphor_color: "green"    # for vintage theme
  rain_density: "medium"     # for matrix theme
  neon_brightness: 0.8       # for neon theme
  glitch_frequency: "low"    # for glitch theme
  accessibility_mode: false
  colorblind_mode: false
  reduce_motion: false
```

## Testing & Validation

### Performance Benchmarks
- Theme switch: <100ms
- Frame update: <16ms (60fps)
- Memory usage: <10MB per theme
- CPU usage: <5% for heaviest effects

### Compatibility Matrix
- Terminal emulators: iTerm2, Alacritty, Windows Terminal, Kitty
- Minimum terminal size: 80x24
- Color support: 256 colors minimum
- Unicode support: Required for special effects

### Quality Assurance
- Data integrity: Effects never corrupt actual data
- Readability: Maintain >90% readability score
- Performance: No impact on trading execution
- Accessibility: WCAG 2.1 AA compliant options