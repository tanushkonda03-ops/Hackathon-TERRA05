import React, { useEffect, useState } from 'react';
import { getScenarioJob, getScenarioResults, runScenario, ScenarioJob, ScenarioResults } from '../services/api';

export const ScenarioPanel: React.FC<{ onRiskMapChange: (map: ScenarioResults['risk_map'] | null) => void }> = ({ onRiskMapChange }) => {
  const [mode, setMode] = useState<'custom' | 'historical_replay'>('custom');
  const [rainfall, setRainfall] = useState(150);
  const [hours, setHours] = useState(6);
  const [job, setJob] = useState<ScenarioJob | null>(null);
  const [result, setResult] = useState<ScenarioResults | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!job || ['COMPLETE', 'FAILED_PHYSICS', 'FAILED_ML', 'FAILED_INPUT'].includes(job.status)) return;
    const timer = window.setTimeout(async () => {
      try {
        const updated = await getScenarioJob(job.simulation_id);
        setError('');
        setJob(updated);
        if (updated.status === 'COMPLETE') setResult(await getScenarioResults(updated.simulation_id));
      } catch (err) {
        setError('Connection interrupted. Retrying scenario status…');
        // Keep polling through transient network errors so a completed SWMM run is not stranded.
        setJob((current) => current ? { ...current } : current);
      }
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [job]);

  const submit = async () => {
    setError(''); setResult(null);
    try {
      const created = mode === 'historical_replay'
        ? await runScenario({ mode, event_id: 'E001' })
        : await runScenario({ mode, total_rainfall_mm: rainfall, duration_minutes: Math.round(hours * 60) });
      setJob(created);
      onRiskMapChange(null);
      if (created.status === 'COMPLETE') setResult(await getScenarioResults(created.simulation_id));
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not create scenario'); }
  };

  useEffect(() => { onRiskMapChange(result?.risk_map ?? null); }, [result, onRiskMapChange]);

  const busy = !!job && !['COMPLETE', 'FAILED_PHYSICS', 'FAILED_ML', 'FAILED_INPUT'].includes(job.status);
  return <section className="absolute top-16 right-3 z-30 w-72 max-h-[78vh] overflow-auto rounded-xl border border-slate-300 bg-white/95 p-3 shadow-xl backdrop-blur font-mono text-[11px]">
    <div className="mb-2 flex items-center justify-between"><strong className="text-slate-900">SWMM → ML SCENARIO</strong><span className="text-[9px] text-slate-500">EPA SWMM 5.2.4</span></div>
    <label className="mb-2 block text-slate-600">Rainfall mode<select className="mt-1 w-full rounded border border-slate-300 p-1.5 text-slate-900" value={mode} onChange={e => setMode(e.target.value as typeof mode)}>
      <option value="custom">Synthetic user-defined scenario</option><option value="historical_replay">Historical replay · E001</option>
    </select></label>
    {mode === 'custom' && <div className="mb-2 grid grid-cols-2 gap-2">
      <label className="text-slate-600">Total rain (mm)<input type="number" min="0.1" max="5000" value={rainfall} onChange={e => setRainfall(Number(e.target.value))} className="mt-1 w-full rounded border border-slate-300 p-1.5 text-slate-900" /></label>
      <label className="text-slate-600">Duration (h)<input type="number" min="0.25" max="27" step="0.25" value={hours} onChange={e => setHours(Number(e.target.value))} className="mt-1 w-full rounded border border-slate-300 p-1.5 text-slate-900" /></label>
    </div>}
    <button disabled={busy} onClick={submit} className="w-full rounded bg-sky-800 p-2 font-bold text-white disabled:opacity-50">{busy ? 'SIMULATION RUNNING…' : 'RUN SWMM + ML'}</button>
    {job && <div className="mt-2 space-y-1 rounded bg-slate-50 p-2 text-slate-700"><div>Status: <b>{job.status}</b> {job.progress != null && `· ${job.progress}%`}</div><div>Source: {job.rainfall_source}</div><div>Rain: {job.rainfall_total_mm.toFixed(1)} mm · {(job.duration_minutes / 60).toFixed(2)} h</div>{job.cache_hit && <div className="font-bold text-emerald-700">Scenario cache hit</div>}{job.error && <div className="text-rose-700">{job.error}</div>}</div>}
    {error && <p className="mt-2 text-rose-700">{error}</p>}
    {result && <div className="mt-2 space-y-2 border-t border-slate-200 pt-2 text-slate-700">
      <div className="grid grid-cols-2 gap-1"><span>Risk-ranked cells</span><b>{result.summary.grid_cells.toLocaleString()}</b><span>High / very high</span><b>{result.summary.high_or_very_high_cells.toLocaleString()}</b><span>Physics-supported</span><b>{result.physics_supported_cells.toLocaleString()}</b><span>Critical asset cells</span><b>{result.summary.critical_asset_cells.toLocaleString()}</b></div>
      <div className="font-bold">Highest ranked cells</div>{result.risk_map.slice(0, 5).map(cell => <div key={cell.grid_id} className="flex justify-between"><span>Grid {cell.grid_id} · {cell.ward}</span><b>{cell.risk_level} · {cell.risk_score.toFixed(3)}</b></div>)}
      <p className="rounded bg-amber-50 p-2 text-[10px] text-amber-900">{result.prediction_semantics}. Hydraulic node depth remains a proxy, not street water depth.</p>
      {result.decision_support.map(item => <p key={item} className="text-[10px]">• {item}</p>)}
    </div>}
  </section>;
};
