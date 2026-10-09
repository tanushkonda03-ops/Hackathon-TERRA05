import React, { useState } from 'react';
import { 
  AlertTriangle, 
  ShieldCheck, 
  Phone, 
  Navigation, 
  Share2, 
  Check, 
  X, 
  ExternalLink,
  Building
} from 'lucide-react';
import { MumbaiLocation } from '../data/locations';
import { MUMBAI_MUNICIPAL_SHELTERS_GEOJSON, MUMBAI_EVACUATION_CORRIDORS_GEOJSON } from '../data/mumbaiGeojson';

interface CitizenAdvisoryModalProps {
  location: MumbaiLocation | null;
  rainfall: number;
  timelineStep: number;
  peakDepthM: number;
  onClose: () => void;
  onSelectEvacuationLayer?: () => void;
}

export const CitizenAdvisoryModal: React.FC<CitizenAdvisoryModalProps> = ({
  location,
  rainfall,
  timelineStep,
  peakDepthM,
  onClose,
  onSelectEvacuationLayer,
}) => {
  const [copied, setCopied] = useState(false);

  // Match nearest shelter
  const locId = location?.id || 'kurla-west';
  const shelters = MUMBAI_MUNICIPAL_SHELTERS_GEOJSON.features;
  const matchedShelter = shelters.find(s => {
    const p = s.properties as Record<string, any> | null;
    if (!p) return false;
    const locality = String(p.locality || '').toLowerCase();
    const ward = String(p.ward || '').toLowerCase();
    const locName = (location?.name || '').toLowerCase();
    const locWard = (location?.ward || '').toLowerCase();
    return locality.includes(locName) || ward.includes(locWard);
  }) || shelters[0];
  const shelterProps = (matchedShelter.properties || {}) as Record<string, any>;

  // Match designated elevated evacuation route
  const corridors = MUMBAI_EVACUATION_CORRIDORS_GEOJSON.features;
  const matchedCorridor = corridors.find(c => {
    const p = c.properties as Record<string, any> | null;
    if (!p) return false;
    const serves = (p.serves as string[]) || [];
    const primaryWard = String(p.primaryWard || '').toLowerCase();
    const locWard = (location?.ward || '').toLowerCase();
    return serves.includes(locId) || primaryWard.includes(locWard);
  }) || corridors[0];
  const corridorProps = (matchedCorridor.properties || {}) as Record<string, any>;

  // Human-interpretable water depth classification
  const getHumanDepthRating = (depthM: number) => {
    if (depthM >= 0.75) {
      return {
        level: 'CRITICAL / LIFE THREATENING',
        color: 'bg-rose-600 text-white',
        badge: 'WAIST-HIGH WATER (>0.8m)',
        carStatus: '❌ VEHICLES COMPLETELY STALLED & FLOATING',
        walkStatus: '❌ DO NOT WALK — UNMARKED MANHOLES & STRONG CURRENTS',
      };
    } else if (depthM >= 0.35) {
      return {
        level: 'SEVERE INUNDATION',
        color: 'bg-amber-600 text-white',
        badge: 'KNEE-DEEP WATER (0.35m - 0.70m)',
        carStatus: '❌ SMALL CARS & SEDANS IMMOBILIZED',
        walkStatus: '⚠️ EXTREME HAZARD — USE ELEVATED FLYOVER ONLY',
      };
    } else if (depthM >= 0.15) {
      return {
        level: 'MODERATE WATERLOGGING',
        color: 'bg-yellow-500 text-slate-950',
        badge: 'ANKLE-DEEP PONDING (0.15m - 0.35m)',
        carStatus: '⚠️ SLOW SPEEDS (SUB-10 KM/H ONLY)',
        walkStatus: '⚠️ SLIPPERY CURRENTS & BLOCKED DRAINS',
      };
    } else {
      return {
        level: 'WATCH / MINIMAL INUNDATION',
        color: 'bg-emerald-600 text-white',
        badge: 'LOCALIZED RUNOFF (<0.15m)',
        carStatus: '✓ PASSABLE WITH CAUTION',
        walkStatus: '✓ SAFE FOOTWEAR ADVISED',
      };
    }
  };

  const depthInfo = getHumanDepthRating(peakDepthM);

  const advisoryText = `⚠️ [BMC CITIZEN FLOOD ALERT] ⚠️
Location: ${location?.name || 'Kurla West'} (${location?.ward || 'Ward L'})
Forecast Rain: ${rainfall} mm/hr | Current Water Depth: ~${peakDepthM.toFixed(2)}m (${depthInfo.badge})
Road Condition: ${depthInfo.carStatus}
Safe Evacuation Route: ${corridorProps.name || 'SCLR Elevated Flyover'} (Elev: ${corridorProps.elevationM || 14}m MSL)
Nearest Municipal Refuge Shelter: ${shelterProps.name || 'BMC Municipal School'} (${shelterProps.facilities || 'Dry Rations, First Aid'})
Emergency Helpline: BMC Disaster Cell: 1916 | Ambulance: 108 | Police: 100
Stay Safe & Keep Phones Charged!`;

  const handleCopyAlert = () => {
    navigator.clipboard.writeText(advisoryText);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  const handleWhatsAppShare = () => {
    const encoded = encodeURIComponent(advisoryText);
    window.open(`https://api.whatsapp.com/send?text=${encoded}`, '_blank');
  };

  return (
    <div 
      className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center p-3 sm:p-5 overflow-y-auto"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
    >
      <div className="bg-white rounded-2xl shadow-float border border-slate-200 max-w-2xl w-full max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header with High-Contrast Citizen Warning Badge */}
        <div className={`p-4 sm:p-5 ${depthInfo.color} flex items-start justify-between relative`}>
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider uppercase bg-black/25 text-white">
                PUBLIC SAFETY ADVISORY · BMC WARD {location?.ward || 'L'}
              </span>
              <span className="text-[10px] font-mono opacity-90">
                {timelineStep === 4 ? '🔴 PEAK FLOOD STAGE' : '⚠️ ACTIVE PROPAGATION'}
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black tracking-tight flex items-center gap-2">
              <AlertTriangle className="w-6 h-6 shrink-0" />
              <span>{location?.name || 'Kurla West'} Flood Warning</span>
            </h2>
            <p className="text-xs sm:text-sm font-medium opacity-95">
              Current Condition: <span className="font-bold underline">{depthInfo.level}</span> — Estimated depth {peakDepthM.toFixed(2)}m
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-full bg-black/20 hover:bg-black/35 text-white transition-colors"
            aria-label="Close Citizen Advisory"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-4 sm:p-5 space-y-4 overflow-y-auto font-sans text-slate-800 text-xs sm:text-sm">
          {/* Section 1: Immediate Travel & Survival Directives */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 space-y-1.5">
              <div className="font-bold text-rose-950 flex items-center gap-1.5 text-xs font-mono uppercase">
                <AlertTriangle className="w-4 h-4 text-rose-700" />
                <span>Vehicle & Transit Status</span>
              </div>
              <div className="text-xs text-rose-900 font-semibold leading-relaxed">
                {depthInfo.carStatus}
              </div>
              <p className="text-[11px] text-rose-800/90 leading-tight">
                Water exceeding 0.3m destroys engines and washes away sedans and two-wheelers. Avoid subways and underpasses entirely.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 space-y-1.5">
              <div className="font-bold text-amber-950 flex items-center gap-1.5 text-xs font-mono uppercase">
                <Navigation className="w-4 h-4 text-amber-700" />
                <span>Pedestrian Safety</span>
              </div>
              <div className="text-xs text-amber-900 font-semibold leading-relaxed">
                {depthInfo.walkStatus}
              </div>
              <p className="text-[11px] text-amber-800/90 leading-tight">
                High risk of displaced manhole covers, electric leakage, and hidden open storm gutters. Stay on high paved ground.
              </p>
            </div>
          </div>

          {/* Section 2: Designated Safe Elevated Evacuation Corridor */}
          <div className="p-4 rounded-xl bg-emerald-50/90 border border-emerald-200 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 font-bold text-emerald-950">
                <ShieldCheck className="w-5 h-5 text-emerald-700" />
                <span className="text-sm">RECOMMENDED DRY EVACUATION ROUTE</span>
              </div>
              <span className="text-[10px] font-mono font-bold bg-emerald-600 text-white px-2 py-0.5 rounded">
                ELEVATION: {corridorProps.elevationM || 14}m MSL
              </span>
            </div>

            <div className="text-xs text-slate-800 font-medium">
              <strong className="text-emerald-900">{corridorProps.name || 'Elevated Bypass Corridor'}</strong>
            </div>

            <div className="text-[11px] text-slate-600 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono">
              <span>Status: <strong className="text-emerald-800">{corridorProps.status || 'OPEN_DRY'}</strong></span>
              <span>Direct Link to: <strong className="text-slate-900">{corridorProps.destinationHospital || 'Hospital Emergency Trauma Center'}</strong></span>
              <span>Length: {corridorProps.lengthKm || 4.2} km</span>
            </div>

            {onSelectEvacuationLayer && (
              <button
                onClick={() => {
                  onSelectEvacuationLayer();
                  onClose();
                }}
                className="mt-1 text-[11px] font-mono font-bold text-emerald-700 hover:text-emerald-900 flex items-center gap-1 underline cursor-pointer"
              >
                <span>View highlighted green evacuation route on 3D map</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Section 3: Nearest Municipal Refuge Shelter */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 font-bold text-slate-900">
                <Building className="w-4 h-4 text-sky-700" />
                <span className="text-xs uppercase font-mono">Nearest High-Ground Municipal Shelter</span>
              </div>
              <span className="text-[10px] font-mono text-slate-600 bg-white border border-slate-200 px-2 py-0.5 rounded">
                Capacity: {shelterProps.capacity || 500} Citizens
              </span>
            </div>

            <div className="text-xs font-bold text-slate-900">
              {shelterProps.name || 'Municipal Refuge Shelter'} ({shelterProps.ward || 'Ward L'})
            </div>

            <div className="text-[11px] text-slate-600 space-y-1">
              <div>📍 Distance: <strong className="text-slate-800">{shelterProps.walkingDistM || '350m'}</strong> (Elev: {shelterProps.elevationM || 12}m MSL)</div>
              <div>⚡ Facilities: <span className="text-slate-700">{shelterProps.facilities || 'Drinking Water, Dry Rations, Generators'}</span></div>
              <div>📞 Shelter Desk: <strong className="text-sky-800 font-mono">{shelterProps.phone || '022-26505109'}</strong></div>
            </div>
          </div>

          {/* Section 4: Urgent Emergency Contacts */}
          <div className="p-3 bg-sky-50 rounded-xl border border-sky-200 flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
            <div className="flex items-center gap-1.5 text-sky-950 font-bold">
              <Phone className="w-4 h-4 text-sky-700" />
              <span>EMERGENCY HELPLINES:</span>
            </div>
            <div className="flex items-center gap-3">
              <a href="tel:1916" className="font-bold text-sky-900 bg-white px-2 py-1 rounded border border-sky-300 hover:bg-sky-100 flex items-center gap-1">
                <span>BMC Cell:</span>
                <span className="text-rose-700 font-extrabold text-sm">1916</span>
              </a>
              <a href="tel:108" className="font-bold text-sky-900 bg-white px-2 py-1 rounded border border-sky-300 hover:bg-sky-100 flex items-center gap-1">
                <span>Ambulance:</span>
                <span className="text-emerald-700 font-extrabold text-sm">108</span>
              </a>
              <a href="tel:100" className="font-bold text-sky-900 bg-white px-2 py-1 rounded border border-sky-300 hover:bg-sky-100 flex items-center gap-1">
                <span>Police:</span>
                <span className="text-slate-900 font-extrabold text-sm">100</span>
              </a>
            </div>
          </div>
        </div>

        {/* Action Footer: WhatsApp & Copy SMS Share buttons */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2.5">
          <div className="text-[11px] text-slate-500 font-mono hidden sm:block">
            Official BMC Disaster Management Cell Broadcast Spec
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              onClick={handleWhatsAppShare}
              className="flex-1 sm:flex-none px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-mono font-bold text-xs flex items-center justify-center gap-1.5 shadow-gis-xs transition-colors"
            >
              <Share2 className="w-3.5 h-3.5" />
              <span>SHARE ON WHATSAPP</span>
            </button>

            <button
              onClick={handleCopyAlert}
              className="flex-1 sm:flex-none px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-mono font-bold text-xs flex items-center justify-center gap-1.5 shadow-gis-xs transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Share2 className="w-3.5 h-3.5" />}
              <span>{copied ? 'COPIED TO CLIPBOARD!' : 'COPY ADVISORY SMS'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
