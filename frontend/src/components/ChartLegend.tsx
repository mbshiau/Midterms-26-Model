/** Custom Recharts <Legend content> renderer.
 *
 * Recharts' default legend derives its item order from internal chart
 * state rather than reliably following <Line> JSX declaration order (in
 * this Recharts version `payload` also isn't an accepted public prop on
 * <Legend>, so it can't just be passed in directly either) -- rendering our
 * own list is the only way to guarantee a specific order (e.g. winner
 * first), matching the built-in look (line-swatch + label, centered row).
 */
export function ChartLegend({ items }: { items: { name: string; color: string }[] }) {
  return (
    <ul
      className="mt-2 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-sm"
      style={{ color: "var(--text-secondary)" }}
    >
      {items.map((item) => (
        <li key={item.name} className="flex items-center gap-1.5">
          <span className="inline-block h-[2px] w-4" style={{ backgroundColor: item.color }} />
          {item.name}
        </li>
      ))}
    </ul>
  );
}
