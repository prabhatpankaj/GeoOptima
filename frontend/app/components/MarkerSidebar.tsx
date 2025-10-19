"use client";

export default function MarkerSidebar({ markers, onRemove }: any) {
  return (
    <div className="mt-4">
      <h3 className="font-semibold mb-2 text-sm">Markers ({markers.length})</h3>
      <div className="space-y-2 max-h-[50vh] overflow-auto">
        {markers.map((m: any) => (
          <div
            key={m.id}
            className="p-2 bg-white border rounded flex items-center justify-between"
          >
            <div>
              <div className="font-medium text-sm">{m.label}</div>
              <div className="text-xs text-slate-500">
                {m.lat.toFixed(4)}, {m.lng.toFixed(4)}
              </div>
            </div>
            <button
              onClick={() => onRemove(m.id)}
              className="text-xs px-2 py-1 bg-red-50 text-red-600 rounded"
            >
              Delete
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
