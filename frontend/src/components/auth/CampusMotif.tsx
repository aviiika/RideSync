/**
 * The network, drawn as a sign-in backdrop.
 *
 * A stylised version of the three campus routes with shuttles running along
 * them, in the same colours the map uses. It previews the product rather than
 * decorating around it, so the first screen already says what the app is.
 *
 * Purely atmosphere: it carries no information, so it is hidden from assistive
 * technology and stops moving when the viewer asks for reduced motion.
 */

const ROUTES = [
  { d: 'M40 210 C 110 150, 150 90, 250 70', color: '#2563eb', delay: '0s' },
  { d: 'M40 210 C 130 230, 190 200, 280 160', color: '#db2777', delay: '-3s' },
  { d: 'M40 210 C 90 260, 180 300, 285 265', color: '#16a34a', delay: '-6s' },
] as const;

const STOPS = [
  [40, 210],
  [250, 70],
  [280, 160],
  [285, 265],
  [136, 137],
  [173, 214],
  [160, 275],
] as const;

export function CampusMotif() {
  return (
    <svg
      viewBox="0 0 320 320"
      className="h-full w-full"
      aria-hidden="true"
      focusable="false"
    >
      {/* Faint grid, so the shapes read as a map rather than an abstract swoosh. */}
      <defs>
        <pattern id="motif-grid" width="32" height="32" patternUnits="userSpaceOnUse">
          <path d="M32 0 L0 0 0 32" fill="none" stroke="currentColor" strokeWidth="0.5" />
        </pattern>
      </defs>
      <rect width="320" height="320" fill="url(#motif-grid)" className="text-white/10" />

      {ROUTES.map((route) => (
        <g key={route.color}>
          <path
            d={route.d}
            fill="none"
            stroke={route.color}
            strokeWidth="5"
            strokeLinecap="round"
            opacity="0.35"
          />
          <path
            d={route.d}
            fill="none"
            stroke={route.color}
            strokeWidth="5"
            strokeLinecap="round"
            className="route-flow"
            style={{ animationDelay: route.delay }}
          />
        </g>
      ))}

      {STOPS.map(([x, y]) => (
        <circle key={`${x}-${y}`} cx={x} cy={y} r="4.5" fill="#ffffff" opacity="0.85" />
      ))}

      {/* The rider, where all three routes meet. */}
      <circle cx="40" cy="210" r="14" fill="#ffffff" className="rider-pulse" opacity="0.35" />
      <circle cx="40" cy="210" r="6.5" fill="#ffffff" />
    </svg>
  );
}
