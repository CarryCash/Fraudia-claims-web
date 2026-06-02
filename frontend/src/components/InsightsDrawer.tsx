import { FileText } from 'lucide-react';

export type ProviderAlert = {
    provider: string;
    alerts: number;
};

export type WeeklyTrendEntry = {
    label: string;
    rojo: number;
    amarillo: number;
};

export type InsightsDrawerProps = {
    onClose: () => void;
    riskDistribution: {
        rojo: number;
        amarillo: number;
        verde: number;
    };
    topProviders: ProviderAlert[];
    weeklyTrend: WeeklyTrendEntry[];
};


export default function InsightsDrawer({
    onClose,
    topProviders,
    weeklyTrend,
}: InsightsDrawerProps) {
    return (
        <div className="fixed inset-0 z-50 flex items-stretch">
            <button
                type="button"
                className="absolute inset-0 bg-black/30 z-0"
                onClick={onClose}
                aria-label="Cerrar insights"
            />
            <aside className="relative z-10 ml-auto w-full max-w-[420px] h-full bg-surface border-l border-outline-variant shadow-2xl overflow-y-auto p-6">
                <div className="flex items-start justify-between gap-4 mb-6">
                    <div>
                        <h2 className="text-headline-sm font-bold text-on-surface">Insights de riesgo</h2>
                        <p className="text-label-sm text-on-surface-variant mt-1">Visión rápida para el analista.</p>
                    </div>
                    <button
                        type="button"
                        className="rounded-full p-2 bg-surface-container-high text-on-surface-variant hover:bg-surface-container-low"
                        onClick={onClose}
                        aria-label="Cerrar panel"
                    >
                        ✕
                    </button>
                </div>

                <div className="rounded-3xl border border-outline-variant bg-surface-container-lowest p-4">
                    <div className="flex items-center justify-between mb-4">
                        <div>
                            <h3 className="text-label-md font-bold text-on-surface">Top proveedores con alertas</h3>
                            <p className="text-label-sm text-on-surface-variant">Más casos rojos/amarillos.</p>
                        </div>
                        <FileText className="text-on-surface-variant" size={20} />
                    </div>
                    <div className="space-y-3">
                        {topProviders.length === 0 ? (
                            <p className="text-label-sm text-on-surface-variant">No hay datos suficientes para calcular el ranking.</p>
                        ) : (
                            topProviders.map((item, index) => (
                                <div key={item.provider} className="flex items-center justify-between gap-3">
                                    <div className="min-w-0">
                                        <p className="text-label-sm font-bold text-on-surface truncate">{index + 1}. {item.provider}</p>
                                        <p className="text-[11px] text-on-surface-variant">Alertas: {item.alerts}</p>
                                    </div>
                                    <div className="text-sm font-bold text-on-surface">{item.alerts}</div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
                <br />

                <div className="rounded-3xl border border-outline-variant bg-surface-container-lowest p-4">
                    <div className="flex items-center justify-between mb-4">
                        <div>
                            <h3 className="text-label-md font-bold text-on-surface">Tendencia semanal</h3>
                            <p className="text-label-sm text-on-surface-variant">Rojos y amarillos en las últimas 6 semanas.</p>
                        </div>
                        <span className="text-label-sm text-on-surface-variant">Semanas</span>
                    </div>
                    <div className="space-y-3">
                        {weeklyTrend.map((week) => {
                            const total = week.rojo + week.amarillo || 1;
                            return (
                                <div key={week.label} className="space-y-2">
                                    <div className="flex items-center justify-between text-label-sm text-on-surface-variant">
                                        <span>{week.label}</span>
                                        <span>{week.rojo + week.amarillo} alertas</span>
                                    </div>
                                    <div className="h-3 bg-surface-container-high rounded-full overflow-hidden flex">
                                        <div className="h-full bg-red-500" style={{ width: `${(week.rojo / total) * 100}%` }} />
                                        <div className="h-full bg-yellow-500" style={{ width: `${(week.amarillo / total) * 100}%` }} />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </aside>
        </div>
    );
}
