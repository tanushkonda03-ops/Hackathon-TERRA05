export interface ModelExplanationFactors {
  elevationContribution: number;
  drainageContribution: number;
  imperviousContribution: number;
  rainfallContribution: number;
}

export interface TimelineImpactMetrics {
  stage: 'T00' | 'T01' | 'T02' | 'T03' | 'T04' | 'T05' | 'T06';
  stageName: string;
  stageDescription: string;
  alertLevel: 'NORMAL' | 'ADVISORY' | 'FLOOD WATCH' | 'FLOOD WARNING' | 'SEVERE FLOOD EMERGENCY';
  rainfallMmHr: number;
  drainStressState: 'OPTIMAL' | 'LOADING' | 'HIGH LOAD' | 'OVERLOADED' | 'SURCHARGING OVERFLOW';
  stressedDrainsCount: number;
  overloadedSegmentsCount: number;
  overflowZonesCount: number;
  floodedAreaKm2: number;
  affectedStructures: number;
  populationAtRisk: number;
  affectedRoadSegments: number;
  criticalFacilitiesExposed: number;
  mithiRiverStatus: 'NORMAL' | 'ELEVATED' | 'HIGH STRESS' | 'BANKFULL / OVERFLOW';
  runoffMm?: number;
  infiltrationMm?: number;
  totalDrainageM3?: number;
  surfaceStorageM3?: number;
  waterBalanceErrorPercent?: number;
}

export interface MumbaiLocation {
  id: string;
  name: string;
  subDistrict: string;
  ward: string;
  gridId?: number;
  lng: number;
  lat: number;
  elevationM: number;
  imperviousRatio: number;
  drainDistanceM: number;
  flowAccumulationPercentile: number;
  description: string;
  citizenAdvice?: string;
  authorityAction?: string;
  explanationFactors: ModelExplanationFactors;
  scenarios: Record<number, {
    probability: number;
    depthM: number;
    interval90: [number, number];
    confidencePercent: number;
    severity: 'SAFE' | 'ADVISORY' | 'WARNING' | 'SEVERE';
    affectedStructures: number;
    populationAtRisk: number;
  }>;
}

export const MUMBAI_GEO_LOCATIONS: MumbaiLocation[] = [
  {
    "id": "ward_a",
    "name": "Colaba & Fort (Ward A)",
    "subDistrict": "Colaba / Marine Drive Basin",
    "ward": "A",
    "gridId": 1201,
    "lng": 72.83,
    "lat": 18.925,
    "elevationM": 3.2,
    "imperviousRatio": 0.88,
    "drainDistanceM": 35,
    "flowAccumulationPercentile": 45,
    "description": "South Mumbai coastal commercial zone including Fort, Colaba, Marine Drive and Gateway of India.",
    "citizenAdvice": "Coastal high-tide alert: Marine Drive promenade experiences sea spray. Coastal roads open with caution.",
    "authorityAction": "Inspect Apollo Bunder tidal sluice gates. Keep emergency suction pumps ready at Sasoon Docks.",
    "scenarios": {
      "25": {
        "probability": 8,
        "depthM": 0.02,
        "interval90": [
          0.01,
          0.05
        ],
        "confidencePercent": 94,
        "severity": "SAFE",
        "affectedStructures": 5,
        "populationAtRisk": 200
      },
      "50": {
        "probability": 25,
        "depthM": 0.12,
        "interval90": [
          0.06,
          0.2
        ],
        "confidencePercent": 90,
        "severity": "ADVISORY",
        "affectedStructures": 20,
        "populationAtRisk": 900
      },
      "100": {
        "probability": 52,
        "depthM": 0.28,
        "interval90": [
          0.18,
          0.4
        ],
        "confidencePercent": 87,
        "severity": "WARNING",
        "affectedStructures": 80,
        "populationAtRisk": 3500
      },
      "150": {
        "probability": 78,
        "depthM": 0.52,
        "interval90": [
          0.38,
          0.68
        ],
        "confidencePercent": 84,
        "severity": "SEVERE",
        "affectedStructures": 210,
        "populationAtRisk": 9200
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_b",
    "name": "Sandhurst Rd & Masjid (Ward B)",
    "subDistrict": "Bunder / Port Catchment",
    "ward": "B",
    "gridId": 2405,
    "lng": 72.84,
    "lat": 18.955,
    "elevationM": 4.1,
    "imperviousRatio": 0.94,
    "drainDistanceM": 28,
    "flowAccumulationPercentile": 62,
    "description": "Dense historic wholesale market zone including Dongri, Masjid Bunder, and Mohammed Ali Road.",
    "citizenAdvice": "Heavy pedestrian crowding. Avoid waterlogged wholesale market lanes along P. D'Mello Road.",
    "authorityAction": "Clear debris from Masjid Bunder railway culverts and stage 2 mobile dewatering units.",
    "scenarios": {
      "25": {
        "probability": 12,
        "depthM": 0.04,
        "interval90": [
          0.02,
          0.08
        ],
        "confidencePercent": 92,
        "severity": "SAFE",
        "affectedStructures": 15,
        "populationAtRisk": 600
      },
      "50": {
        "probability": 42,
        "depthM": 0.22,
        "interval90": [
          0.12,
          0.35
        ],
        "confidencePercent": 89,
        "severity": "WARNING",
        "affectedStructures": 65,
        "populationAtRisk": 2800
      },
      "100": {
        "probability": 75,
        "depthM": 0.46,
        "interval90": [
          0.32,
          0.62
        ],
        "confidencePercent": 86,
        "severity": "SEVERE",
        "affectedStructures": 190,
        "populationAtRisk": 8500
      },
      "150": {
        "probability": 90,
        "depthM": 0.74,
        "interval90": [
          0.55,
          0.96
        ],
        "confidencePercent": 83,
        "severity": "SEVERE",
        "affectedStructures": 420,
        "populationAtRisk": 18000
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_c",
    "name": "Kalbadevi & Bhuleshwar (Ward C)",
    "subDistrict": "Chira Bazaar / Girgaon Basin",
    "ward": "C",
    "gridId": 3102,
    "lng": 72.825,
    "lat": 18.948,
    "elevationM": 3.8,
    "imperviousRatio": 0.96,
    "drainDistanceM": 22,
    "flowAccumulationPercentile": 74,
    "description": "Ultra-dense commercial trading district with 95%+ concrete coverage and zero infiltration.",
    "citizenAdvice": "Ground-floor shops should elevate stock by 1 ft. Avoid narrow lanes of Chira Bazaar during peak downpour.",
    "authorityAction": "Continuous desilting of Kalbadevi box drains. Coordinate with traffic police for lane closures.",
    "scenarios": {
      "25": {
        "probability": 18,
        "depthM": 0.06,
        "interval90": [
          0.03,
          0.11
        ],
        "confidencePercent": 91,
        "severity": "SAFE",
        "affectedStructures": 30,
        "populationAtRisk": 1200
      },
      "50": {
        "probability": 55,
        "depthM": 0.26,
        "interval90": [
          0.15,
          0.4
        ],
        "confidencePercent": 88,
        "severity": "WARNING",
        "affectedStructures": 110,
        "populationAtRisk": 4800
      },
      "100": {
        "probability": 86,
        "depthM": 0.58,
        "interval90": [
          0.42,
          0.78
        ],
        "confidencePercent": 85,
        "severity": "SEVERE",
        "affectedStructures": 310,
        "populationAtRisk": 14000
      },
      "150": {
        "probability": 96,
        "depthM": 0.88,
        "interval90": [
          0.68,
          1.12
        ],
        "confidencePercent": 82,
        "severity": "SEVERE",
        "affectedStructures": 580,
        "populationAtRisk": 26000
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_d",
    "name": "Grant Rd & Malabar Hill (Ward D)",
    "subDistrict": "Tardeo / Walkeshwar Basin",
    "ward": "D",
    "gridId": 4150,
    "lng": 72.81,
    "lat": 18.965,
    "elevationM": 5.4,
    "imperviousRatio": 0.82,
    "drainDistanceM": 30,
    "flowAccumulationPercentile": 68,
    "description": "Steep hillside runoff flowing from Malabar Hill and Cumballa Hill directly into Tardeo saucer basin.",
    "citizenAdvice": "Rapid runoff descent from hills: Tardeo and Nana Chowk face fast pooling water. Avoid pedestrian underpasses.",
    "authorityAction": "Ensure high-capacity drainage outfalls at Haji Ali are clear of plastic waste.",
    "scenarios": {
      "25": {
        "probability": 14,
        "depthM": 0.05,
        "interval90": [
          0.02,
          0.09
        ],
        "confidencePercent": 92,
        "severity": "SAFE",
        "affectedStructures": 20,
        "populationAtRisk": 800
      },
      "50": {
        "probability": 50,
        "depthM": 0.24,
        "interval90": [
          0.14,
          0.38
        ],
        "confidencePercent": 88,
        "severity": "WARNING",
        "affectedStructures": 95,
        "populationAtRisk": 4100
      },
      "100": {
        "probability": 84,
        "depthM": 0.54,
        "interval90": [
          0.38,
          0.72
        ],
        "confidencePercent": 85,
        "severity": "SEVERE",
        "affectedStructures": 280,
        "populationAtRisk": 12500
      },
      "150": {
        "probability": 95,
        "depthM": 0.85,
        "interval90": [
          0.65,
          1.1
        ],
        "confidencePercent": 82,
        "severity": "SEVERE",
        "affectedStructures": 530,
        "populationAtRisk": 23500
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_e",
    "name": "Byculla & Mumbai Central (Ward E)",
    "subDistrict": "Mazgaon / Nagpada Basin",
    "ward": "E",
    "gridId": 5210,
    "lng": 72.835,
    "lat": 18.975,
    "elevationM": 4.2,
    "imperviousRatio": 0.9,
    "drainDistanceM": 26,
    "flowAccumulationPercentile": 65,
    "description": "Low-lying historic hub connecting Byculla, Mazgaon, and Mumbai Central railway station corridors.",
    "citizenAdvice": "Low-lying road sections near Byculla station submerge during 50mm+ rain. Use Dr. BA Road flyover.",
    "authorityAction": "Deploy 3 dewatering pumps at Byculla railway culvert and Britannia pumping station.",
    "scenarios": {
      "25": {
        "probability": 12,
        "depthM": 0.04,
        "interval90": [
          0.02,
          0.08
        ],
        "confidencePercent": 93,
        "severity": "SAFE",
        "affectedStructures": 18,
        "populationAtRisk": 750
      },
      "50": {
        "probability": 46,
        "depthM": 0.21,
        "interval90": [
          0.11,
          0.33
        ],
        "confidencePercent": 89,
        "severity": "WARNING",
        "affectedStructures": 75,
        "populationAtRisk": 3200
      },
      "100": {
        "probability": 79,
        "depthM": 0.48,
        "interval90": [
          0.34,
          0.65
        ],
        "confidencePercent": 86,
        "severity": "SEVERE",
        "affectedStructures": 230,
        "populationAtRisk": 10200
      },
      "150": {
        "probability": 92,
        "depthM": 0.78,
        "interval90": [
          0.58,
          1.02
        ],
        "confidencePercent": 83,
        "severity": "SEVERE",
        "affectedStructures": 470,
        "populationAtRisk": 21000
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_fs",
    "name": "Dadar & Hindmata (Ward F/S)",
    "subDistrict": "Dr. Ambedkar Road / Parel Basin",
    "ward": "F/S",
    "gridId": 6400,
    "lng": 72.845,
    "lat": 19.005,
    "elevationM": 3.6,
    "imperviousRatio": 0.92,
    "drainDistanceM": 20,
    "flowAccumulationPercentile": 88,
    "description": "Historic natural saucer depression: Hindmata flyover underpass and Lalbaug/Parel arterial junction.",
    "citizenAdvice": "Chronic saucer depression: Avoid Hindmata underpass. Use elevated flyovers on Dr. Ambedkar Road.",
    "authorityAction": "Activate underground holding tank pumps at Pramod Mahajan Park. Divert BEST buses via flyovers.",
    "scenarios": {
      "25": {
        "probability": 16,
        "depthM": 0.06,
        "interval90": [
          0.02,
          0.12
        ],
        "confidencePercent": 91,
        "severity": "SAFE",
        "affectedStructures": 25,
        "populationAtRisk": 1100
      },
      "50": {
        "probability": 58,
        "depthM": 0.28,
        "interval90": [
          0.16,
          0.42
        ],
        "confidencePercent": 88,
        "severity": "WARNING",
        "affectedStructures": 125,
        "populationAtRisk": 5500
      },
      "100": {
        "probability": 88,
        "depthM": 0.62,
        "interval90": [
          0.45,
          0.82
        ],
        "confidencePercent": 85,
        "severity": "SEVERE",
        "affectedStructures": 360,
        "populationAtRisk": 16000
      },
      "150": {
        "probability": 98,
        "depthM": 0.95,
        "interval90": [
          0.72,
          1.22
        ],
        "confidencePercent": 82,
        "severity": "SEVERE",
        "affectedStructures": 680,
        "populationAtRisk": 31000
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_fn",
    "name": "Sion Circle & Matunga (Ward F/N)",
    "subDistrict": "King's Circle / Gandhi Market Basin",
    "ward": "F/N",
    "gridId": 7800,
    "lng": 72.858,
    "lat": 19.035,
    "elevationM": 3.4,
    "imperviousRatio": 0.89,
    "drainDistanceM": 18,
    "flowAccumulationPercentile": 92,
    "description": "Severe saucer basin: Gandhi Market and King's Circle rail culvert bottleneck connecting Sion and Matunga.",
    "citizenAdvice": "Gandhi Market and King's Circle rail underpass pool fast. Harbor Line train services may face delays.",
    "authorityAction": "Run Gandhi Market mini-pumping station at maximum output. Keep rescue trucks near Sion Hospital.",
    "scenarios": {
      "25": {
        "probability": 20,
        "depthM": 0.08,
        "interval90": [
          0.03,
          0.14
        ],
        "confidencePercent": 90,
        "severity": "SAFE",
        "affectedStructures": 35,
        "populationAtRisk": 1500
      },
      "50": {
        "probability": 65,
        "depthM": 0.32,
        "interval90": [
          0.2,
          0.48
        ],
        "confidencePercent": 87,
        "severity": "WARNING",
        "affectedStructures": 160,
        "populationAtRisk": 7200
      },
      "100": {
        "probability": 92,
        "depthM": 0.7,
        "interval90": [
          0.52,
          0.92
        ],
        "confidencePercent": 84,
        "severity": "SEVERE",
        "affectedStructures": 420,
        "populationAtRisk": 19000
      },
      "150": {
        "probability": 99,
        "depthM": 1.05,
        "interval90": [
          0.82,
          1.35
        ],
        "confidencePercent": 81,
        "severity": "SEVERE",
        "affectedStructures": 790,
        "populationAtRisk": 36000
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_gs",
    "name": "Worli & Lower Parel (Ward G/S)",
    "subDistrict": "Worli Naka / Mahalaxmi Basin",
    "ward": "G/S",
    "gridId": 8950,
    "lng": 72.82,
    "lat": 19.005,
    "elevationM": 4.6,
    "imperviousRatio": 0.86,
    "drainDistanceM": 32,
    "flowAccumulationPercentile": 58,
    "description": "High-rise corporate corridor and coastal zone spanning Worli, Lower Parel, and Mahalaxmi.",
    "citizenAdvice": "Worli Naka and Senapati Bapat Marg have localized curb pooling. Lower Parel offices stay vigilant.",
    "authorityAction": "Operate Love Grove and Cleaveland Bunder pumping stations to discharge water into Arabian Sea.",
    "scenarios": {
      "25": {
        "probability": 10,
        "depthM": 0.03,
        "interval90": [
          0.01,
          0.07
        ],
        "confidencePercent": 93,
        "severity": "SAFE",
        "affectedStructures": 12,
        "populationAtRisk": 500
      },
      "50": {
        "probability": 38,
        "depthM": 0.18,
        "interval90": [
          0.09,
          0.28
        ],
        "confidencePercent": 89,
        "severity": "WARNING",
        "affectedStructures": 55,
        "populationAtRisk": 2400
      },
      "100": {
        "probability": 72,
        "depthM": 0.42,
        "interval90": [
          0.28,
          0.58
        ],
        "confidencePercent": 86,
        "severity": "SEVERE",
        "affectedStructures": 170,
        "populationAtRisk": 7600
      },
      "150": {
        "probability": 88,
        "depthM": 0.68,
        "interval90": [
          0.48,
          0.9
        ],
        "confidencePercent": 83,
        "severity": "SEVERE",
        "affectedStructures": 380,
        "populationAtRisk": 16500
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_gn",
    "name": "Dharavi & Mahim (Ward G/N)",
    "subDistrict": "90-Ft Road / Mahim Creek Basin",
    "ward": "G/N",
    "gridId": 10120,
    "lng": 72.85,
    "lat": 19.042,
    "elevationM": 3.1,
    "imperviousRatio": 0.95,
    "drainDistanceM": 16,
    "flowAccumulationPercentile": 90,
    "description": "Ultra-dense catchment bordered by Mahim Creek, Dharavi 90-Ft Road, and Western Railway culverts.",
    "citizenAdvice": "Ground-floor workshops and homes should raise machinery. Avoid unbarricaded drain channels.",
    "authorityAction": "Station mobile evacuation boats on stand-by. Inspect Mahim Creek outfall flap gates.",
    "scenarios": {
      "25": {
        "probability": 22,
        "depthM": 0.09,
        "interval90": [
          0.04,
          0.15
        ],
        "confidencePercent": 90,
        "severity": "SAFE",
        "affectedStructures": 45,
        "populationAtRisk": 2000
      },
      "50": {
        "probability": 68,
        "depthM": 0.35,
        "interval90": [
          0.22,
          0.52
        ],
        "confidencePercent": 87,
        "severity": "WARNING",
        "affectedStructures": 190,
        "populationAtRisk": 8800
      },
      "100": {
        "probability": 94,
        "depthM": 0.75,
        "interval90": [
          0.55,
          0.98
        ],
        "confidencePercent": 84,
        "severity": "SEVERE",
        "affectedStructures": 490,
        "populationAtRisk": 22500
      },
      "150": {
        "probability": 99,
        "depthM": 1.1,
        "interval90": [
          0.85,
          1.42
        ],
        "confidencePercent": 81,
        "severity": "SEVERE",
        "affectedStructures": 880,
        "populationAtRisk": 41000
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_he",
    "name": "BKC & Kalanagar (Ward H/E)",
    "subDistrict": "Bandra-Kurla Complex / Vakola Basin",
    "ward": "H/E",
    "gridId": 11500,
    "lng": 72.86,
    "lat": 19.065,
    "elevationM": 4.0,
    "imperviousRatio": 0.91,
    "drainDistanceM": 24,
    "flowAccumulationPercentile": 82,
    "description": "Financial epicenter including BKC, Kalanagar, Vakola, and Santacruz East along Mithi River bank.",
    "citizenAdvice": "BKC connector and Kalanagar underpass pool fast during cloudbursts. Use elevated Western Express Highway.",
    "authorityAction": "Check Vakola nallah holding capacity. Stage suction tankers at BKC G-Block.",
    "scenarios": {
      "25": {
        "probability": 15,
        "depthM": 0.05,
        "interval90": [
          0.02,
          0.1
        ],
        "confidencePercent": 91,
        "severity": "SAFE",
        "affectedStructures": 20,
        "populationAtRisk": 900
      },
      "50": {
        "probability": 52,
        "depthM": 0.25,
        "interval90": [
          0.14,
          0.38
        ],
        "confidencePercent": 88,
        "severity": "WARNING",
        "affectedStructures": 90,
        "populationAtRisk": 4000
      },
      "100": {
        "probability": 82,
        "depthM": 0.52,
        "interval90": [
          0.36,
          0.7
        ],
        "confidencePercent": 85,
        "severity": "SEVERE",
        "affectedStructures": 260,
        "populationAtRisk": 11500
      },
      "150": {
        "probability": 94,
        "depthM": 0.82,
        "interval90": [
          0.62,
          1.06
        ],
        "confidencePercent": 82,
        "severity": "SEVERE",
        "affectedStructures": 510,
        "populationAtRisk": 23000
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_hw",
    "name": "Bandra & Milan Subway (Ward H/W)",
    "subDistrict": "Santacruz West / Khar Basin",
    "ward": "H/W",
    "gridId": 12800,
    "lng": 72.835,
    "lat": 19.06,
    "elevationM": 3.8,
    "imperviousRatio": 0.87,
    "drainDistanceM": 20,
    "flowAccumulationPercentile": 86,
    "description": "Sunken railway subway chronic flood spot: Milan Subway (Santacruz), Khar Danda, and SV Road.",
    "citizenAdvice": "Milan Subway closed to vehicular traffic above 30mm rain. Divert via SV Road flyover.",
    "authorityAction": "Operate Milan Subway dedicated dewatering pumps (2000 m3/hr). Place physical height barriers.",
    "scenarios": {
      "25": {
        "probability": 18,
        "depthM": 0.07,
        "interval90": [
          0.03,
          0.13
        ],
        "confidencePercent": 90,
        "severity": "SAFE",
        "affectedStructures": 30,
        "populationAtRisk": 1300
      },
      "50": {
        "probability": 62,
        "depthM": 0.3,
        "interval90": [
          0.18,
          0.45
        ],
        "confidencePercent": 87,
        "severity": "WARNING",
        "affectedStructures": 140,
        "populationAtRisk": 6200
      },
      "100": {
        "probability": 90,
        "depthM": 0.68,
        "interval90": [
          0.48,
          0.88
        ],
        "confidencePercent": 84,
        "severity": "SEVERE",
        "affectedStructures": 380,
        "populationAtRisk": 17000
      },
      "150": {
        "probability": 97,
        "depthM": 1.0,
        "interval90": [
          0.75,
          1.3
        ],
        "confidencePercent": 81,
        "severity": "SEVERE",
        "affectedStructures": 720,
        "populationAtRisk": 32500
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_ke",
    "name": "Andheri East & Saki Naka (Ward K/E)",
    "subDistrict": "MIDC / Marol / Airport Basin",
    "ward": "K/E",
    "gridId": 14200,
    "lng": 72.87,
    "lat": 19.115,
    "elevationM": 7.5,
    "imperviousRatio": 0.85,
    "drainDistanceM": 36,
    "flowAccumulationPercentile": 64,
    "description": "Industrial and airport corridor: MIDC, Marol, Saki Naka junction, and Metro Line 1 corridor.",
    "citizenAdvice": "Saki Naka junction and Asalpha slopes face fast sheet runoff. Slow down near Metro pillars.",
    "authorityAction": "Inspect airport perimeter nullahs. Keep dewatering team stationed at Saki Naka metro undercroft.",
    "scenarios": {
      "25": {
        "probability": 10,
        "depthM": 0.03,
        "interval90": [
          0.01,
          0.07
        ],
        "confidencePercent": 93,
        "severity": "SAFE",
        "affectedStructures": 15,
        "populationAtRisk": 650
      },
      "50": {
        "probability": 40,
        "depthM": 0.19,
        "interval90": [
          0.1,
          0.3
        ],
        "confidencePercent": 89,
        "severity": "WARNING",
        "affectedStructures": 60,
        "populationAtRisk": 2600
      },
      "100": {
        "probability": 74,
        "depthM": 0.44,
        "interval90": [
          0.3,
          0.6
        ],
        "confidencePercent": 86,
        "severity": "SEVERE",
        "affectedStructures": 180,
        "populationAtRisk": 8000
      },
      "150": {
        "probability": 89,
        "depthM": 0.7,
        "interval90": [
          0.5,
          0.94
        ],
        "confidencePercent": 83,
        "severity": "SEVERE",
        "affectedStructures": 400,
        "populationAtRisk": 17500
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_kw",
    "name": "Andheri West & Subway (Ward K/W)",
    "subDistrict": "Andheri Subway / Juhu Basin",
    "ward": "K/W",
    "gridId": 16500,
    "lng": 72.83,
    "lat": 19.12,
    "elevationM": 3.5,
    "imperviousRatio": 0.88,
    "drainDistanceM": 22,
    "flowAccumulationPercentile": 89,
    "description": "High-risk sunken underpass: Andheri Subway, SV Road, JVPD Scheme, and Versova Creek basin.",
    "citizenAdvice": "Andheri Subway is high risk: avoid completely during heavy downpours. Divert via Gokhale Bridge.",
    "authorityAction": "Activate Andheri Subway automated pump house and boom barrier. Divert SV Road traffic.",
    "scenarios": {
      "25": {
        "probability": 20,
        "depthM": 0.08,
        "interval90": [
          0.03,
          0.14
        ],
        "confidencePercent": 90,
        "severity": "SAFE",
        "affectedStructures": 35,
        "populationAtRisk": 1600
      },
      "50": {
        "probability": 66,
        "depthM": 0.34,
        "interval90": [
          0.2,
          0.5
        ],
        "confidencePercent": 87,
        "severity": "WARNING",
        "affectedStructures": 170,
        "populationAtRisk": 7800
      },
      "100": {
        "probability": 93,
        "depthM": 0.74,
        "interval90": [
          0.54,
          0.96
        ],
        "confidencePercent": 84,
        "severity": "SEVERE",
        "affectedStructures": 440,
        "populationAtRisk": 20000
      },
      "150": {
        "probability": 98,
        "depthM": 1.08,
        "interval90": [
          0.84,
          1.38
        ],
        "confidencePercent": 81,
        "severity": "SEVERE",
        "affectedStructures": 810,
        "populationAtRisk": 37000
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_ps",
    "name": "Goregaon (Ward P/S)",
    "subDistrict": "Oshiwara River / SV Road Basin",
    "ward": "P/S",
    "gridId": 19000,
    "lng": 72.85,
    "lat": 19.16,
    "elevationM": 6.8,
    "imperviousRatio": 0.81,
    "drainDistanceM": 38,
    "flowAccumulationPercentile": 65,
    "description": "Western suburb catchment spanning Goregaon West, Oshiwara river basin, and SV Road junction.",
    "citizenAdvice": "SV Road near Goregaon station and Oshiwara bridge experience water accumulation. Use Link Road.",
    "authorityAction": "Maintain Oshiwara River desilted channels and check flood gates near Inorbit mall.",
    "scenarios": {
      "25": {
        "probability": 10,
        "depthM": 0.03,
        "interval90": [
          0.01,
          0.07
        ],
        "confidencePercent": 93,
        "severity": "SAFE",
        "affectedStructures": 15,
        "populationAtRisk": 600
      },
      "50": {
        "probability": 42,
        "depthM": 0.2,
        "interval90": [
          0.1,
          0.32
        ],
        "confidencePercent": 89,
        "severity": "WARNING",
        "affectedStructures": 65,
        "populationAtRisk": 2900
      },
      "100": {
        "probability": 76,
        "depthM": 0.46,
        "interval90": [
          0.32,
          0.64
        ],
        "confidencePercent": 86,
        "severity": "SEVERE",
        "affectedStructures": 200,
        "populationAtRisk": 8900
      },
      "150": {
        "probability": 90,
        "depthM": 0.74,
        "interval90": [
          0.54,
          0.98
        ],
        "confidencePercent": 83,
        "severity": "SEVERE",
        "affectedStructures": 430,
        "populationAtRisk": 19000
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_pn",
    "name": "Malad & Subway (Ward P/N)",
    "subDistrict": "Malad Subway / Marve Basin",
    "ward": "P/N",
    "gridId": 21500,
    "lng": 72.845,
    "lat": 19.185,
    "elevationM": 4.8,
    "imperviousRatio": 0.83,
    "drainDistanceM": 30,
    "flowAccumulationPercentile": 84,
    "description": "Major suburban residential zone with critical sunken culvert: Malad Subway connecting WEH and SV Road.",
    "citizenAdvice": "Malad Subway closes during severe downpour. Use elevated flyovers on Western Express Highway.",
    "authorityAction": "Station 2 high-flow mobile pumps at Malad Subway. Monitor Marve creek tidal outfalls.",
    "scenarios": {
      "25": {
        "probability": 14,
        "depthM": 0.05,
        "interval90": [
          0.02,
          0.1
        ],
        "confidencePercent": 92,
        "severity": "SAFE",
        "affectedStructures": 25,
        "populationAtRisk": 1000
      },
      "50": {
        "probability": 54,
        "depthM": 0.26,
        "interval90": [
          0.15,
          0.4
        ],
        "confidencePercent": 88,
        "severity": "WARNING",
        "affectedStructures": 105,
        "populationAtRisk": 4600
      },
      "100": {
        "probability": 84,
        "depthM": 0.55,
        "interval90": [
          0.38,
          0.74
        ],
        "confidencePercent": 85,
        "severity": "SEVERE",
        "affectedStructures": 290,
        "populationAtRisk": 13000
      },
      "150": {
        "probability": 95,
        "depthM": 0.86,
        "interval90": [
          0.65,
          1.12
        ],
        "confidencePercent": 82,
        "severity": "SEVERE",
        "affectedStructures": 550,
        "populationAtRisk": 24500
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_rs",
    "name": "Kandivali & Poisar (Ward R/S)",
    "subDistrict": "Poisar River / Charkop Basin",
    "ward": "R/S",
    "gridId": 26000,
    "lng": 72.845,
    "lat": 19.205,
    "elevationM": 5.2,
    "imperviousRatio": 0.84,
    "drainDistanceM": 28,
    "flowAccumulationPercentile": 80,
    "description": "Suburban basin spanning Kandivali, Charkop, and Poisar River overflow zone.",
    "citizenAdvice": "Low-lying settlements near Poisar riverbanks face overflow risk. Move valuables to higher floors.",
    "authorityAction": "Check Poisar River retaining wall gates and clear culvert grates along SV Road.",
    "scenarios": {
      "25": {
        "probability": 12,
        "depthM": 0.04,
        "interval90": [
          0.02,
          0.08
        ],
        "confidencePercent": 92,
        "severity": "SAFE",
        "affectedStructures": 20,
        "populationAtRisk": 850
      },
      "50": {
        "probability": 48,
        "depthM": 0.23,
        "interval90": [
          0.12,
          0.35
        ],
        "confidencePercent": 88,
        "severity": "WARNING",
        "affectedStructures": 80,
        "populationAtRisk": 3500
      },
      "100": {
        "probability": 80,
        "depthM": 0.5,
        "interval90": [
          0.35,
          0.68
        ],
        "confidencePercent": 85,
        "severity": "SEVERE",
        "affectedStructures": 240,
        "populationAtRisk": 10800
      },
      "150": {
        "probability": 93,
        "depthM": 0.8,
        "interval90": [
          0.6,
          1.04
        ],
        "confidencePercent": 82,
        "severity": "SEVERE",
        "affectedStructures": 480,
        "populationAtRisk": 21500
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_rc",
    "name": "Borivali & Gorai (Ward R/C)",
    "subDistrict": "Dahisar River / Gorai Creek Basin",
    "ward": "R/C",
    "gridId": 31000,
    "lng": 72.855,
    "lat": 19.23,
    "elevationM": 8.2,
    "imperviousRatio": 0.72,
    "drainDistanceM": 45,
    "flowAccumulationPercentile": 52,
    "description": "Northern suburb with large green/park buffer (SGNP) and Gorai creek tidal boundary.",
    "citizenAdvice": "Generally safe higher ground. Minor waterlogging near Borivali West station market.",
    "authorityAction": "Monitor Gorai Creek tidal outfalls and ensure National Park storm runoff bypass is clear.",
    "scenarios": {
      "25": {
        "probability": 6,
        "depthM": 0.02,
        "interval90": [
          0.01,
          0.04
        ],
        "confidencePercent": 95,
        "severity": "SAFE",
        "affectedStructures": 8,
        "populationAtRisk": 300
      },
      "50": {
        "probability": 28,
        "depthM": 0.14,
        "interval90": [
          0.07,
          0.22
        ],
        "confidencePercent": 90,
        "severity": "ADVISORY",
        "affectedStructures": 35,
        "populationAtRisk": 1500
      },
      "100": {
        "probability": 58,
        "depthM": 0.34,
        "interval90": [
          0.22,
          0.48
        ],
        "confidencePercent": 87,
        "severity": "WARNING",
        "affectedStructures": 110,
        "populationAtRisk": 4900
      },
      "150": {
        "probability": 80,
        "depthM": 0.56,
        "interval90": [
          0.4,
          0.76
        ],
        "confidencePercent": 84,
        "severity": "SEVERE",
        "affectedStructures": 250,
        "populationAtRisk": 11200
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_rn",
    "name": "Dahisar (Ward R/N)",
    "subDistrict": "Dahisar Checknaka / River Basin",
    "ward": "R/N",
    "gridId": 36000,
    "lng": 72.86,
    "lat": 19.255,
    "elevationM": 7.1,
    "imperviousRatio": 0.75,
    "drainDistanceM": 40,
    "flowAccumulationPercentile": 59,
    "description": "Northernmost municipal boundary of Mumbai bordering Mira-Bhayandar across Dahisar River.",
    "citizenAdvice": "Dahisar subway and toll plaza experience slow traffic during heavy downpours. Drive with caution.",
    "authorityAction": "Clear Dahisar River culverts near railway line and maintain flood barrier at Ketkipada.",
    "scenarios": {
      "25": {
        "probability": 8,
        "depthM": 0.03,
        "interval90": [
          0.01,
          0.05
        ],
        "confidencePercent": 94,
        "severity": "SAFE",
        "affectedStructures": 10,
        "populationAtRisk": 400
      },
      "50": {
        "probability": 34,
        "depthM": 0.16,
        "interval90": [
          0.08,
          0.25
        ],
        "confidencePercent": 90,
        "severity": "WARNING",
        "affectedStructures": 45,
        "populationAtRisk": 1900
      },
      "100": {
        "probability": 66,
        "depthM": 0.38,
        "interval90": [
          0.25,
          0.54
        ],
        "confidencePercent": 86,
        "severity": "SEVERE",
        "affectedStructures": 130,
        "populationAtRisk": 5800
      },
      "150": {
        "probability": 85,
        "depthM": 0.62,
        "interval90": [
          0.45,
          0.84
        ],
        "confidencePercent": 83,
        "severity": "SEVERE",
        "affectedStructures": 300,
        "populationAtRisk": 13500
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_l",
    "name": "Kurla West & Bail Bazar (Ward L)",
    "subDistrict": "Mithi River Basin / Kurla-Kalina Catchment",
    "ward": "L",
    "gridId": 23988,
    "lng": 72.875,
    "lat": 19.068,
    "elevationM": 3.8,
    "imperviousRatio": 0.88,
    "drainDistanceM": 20,
    "flowAccumulationPercentile": 94,
    "description": "Mumbai's #1 chronic flood epicenter: Mithi River saucer basin, Bail Bazar, and LBS Marg.",
    "citizenAdvice": "High risk zone: Bail Bazar and Kurla Station submerge fast. Evacuate ground floor if Mithi river alerts sound.",
    "authorityAction": "Open Mithi River floodgates at Kranti Nagar. Stage 4 high-capacity pumps at Bail Bazar and CST Road.",
    "scenarios": {
      "25": {
        "probability": 25,
        "depthM": 0.1,
        "interval90": [
          0.04,
          0.18
        ],
        "confidencePercent": 90,
        "severity": "SAFE",
        "affectedStructures": 50,
        "populationAtRisk": 2200
      },
      "50": {
        "probability": 72,
        "depthM": 0.38,
        "interval90": [
          0.25,
          0.56
        ],
        "confidencePercent": 87,
        "severity": "WARNING",
        "affectedStructures": 210,
        "populationAtRisk": 9500
      },
      "100": {
        "probability": 96,
        "depthM": 0.82,
        "interval90": [
          0.6,
          1.08
        ],
        "confidencePercent": 84,
        "severity": "SEVERE",
        "affectedStructures": 580,
        "populationAtRisk": 26000
      },
      "150": {
        "probability": 99,
        "depthM": 1.25,
        "interval90": [
          0.98,
          1.62
        ],
        "confidencePercent": 81,
        "severity": "SEVERE",
        "affectedStructures": 1100,
        "populationAtRisk": 52000
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_mw",
    "name": "Chembur & Amar Mahal (Ward M/W)",
    "subDistrict": "Eastern Express Highway / Shell Colony Basin",
    "ward": "M/W",
    "gridId": 25100,
    "lng": 72.898,
    "lat": 19.062,
    "elevationM": 4.5,
    "imperviousRatio": 0.87,
    "drainDistanceM": 26,
    "flowAccumulationPercentile": 78,
    "description": "Key arterial junction: Amar Mahal flyover underpass, Tilak Nagar railway culverts, and Shell Colony.",
    "citizenAdvice": "Amar Mahal junction and Shell Colony experience slow traffic. Use elevated Santa Cruz-Chembur Link Road (SCLR).",
    "authorityAction": "Deploy traffic marshals at Amar Mahal roundabout. Run dewatering pumps at Shell Colony culvert.",
    "scenarios": {
      "25": {
        "probability": 15,
        "depthM": 0.05,
        "interval90": [
          0.02,
          0.1
        ],
        "confidencePercent": 91,
        "severity": "SAFE",
        "affectedStructures": 20,
        "populationAtRisk": 850
      },
      "50": {
        "probability": 52,
        "depthM": 0.25,
        "interval90": [
          0.14,
          0.38
        ],
        "confidencePercent": 88,
        "severity": "WARNING",
        "affectedStructures": 85,
        "populationAtRisk": 3800
      },
      "100": {
        "probability": 82,
        "depthM": 0.52,
        "interval90": [
          0.36,
          0.7
        ],
        "confidencePercent": 85,
        "severity": "SEVERE",
        "affectedStructures": 250,
        "populationAtRisk": 11200
      },
      "150": {
        "probability": 94,
        "depthM": 0.82,
        "interval90": [
          0.62,
          1.06
        ],
        "confidencePercent": 82,
        "severity": "SEVERE",
        "affectedStructures": 500,
        "populationAtRisk": 22500
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_me",
    "name": "Govandi & Mankhurd (Ward M/E)",
    "subDistrict": "Thane Creek / Shivaji Nagar Basin",
    "ward": "M/E",
    "gridId": 27200,
    "lng": 72.92,
    "lat": 19.055,
    "elevationM": 4.1,
    "imperviousRatio": 0.89,
    "drainDistanceM": 24,
    "flowAccumulationPercentile": 75,
    "description": "High-density residential and creek boundary zone spanning Govandi, Deonar, and Mankhurd.",
    "citizenAdvice": "Low-lying lanes in Shivaji Nagar experience water buildup. Avoid low footpaths near nallahs.",
    "authorityAction": "Operate Mankhurd creek outfall gates and stage 2 rescue teams near Govandi station.",
    "scenarios": {
      "25": {
        "probability": 14,
        "depthM": 0.05,
        "interval90": [
          0.02,
          0.09
        ],
        "confidencePercent": 92,
        "severity": "SAFE",
        "affectedStructures": 22,
        "populationAtRisk": 950
      },
      "50": {
        "probability": 48,
        "depthM": 0.22,
        "interval90": [
          0.12,
          0.34
        ],
        "confidencePercent": 88,
        "severity": "WARNING",
        "affectedStructures": 78,
        "populationAtRisk": 3400
      },
      "100": {
        "probability": 78,
        "depthM": 0.48,
        "interval90": [
          0.34,
          0.65
        ],
        "confidencePercent": 85,
        "severity": "SEVERE",
        "affectedStructures": 220,
        "populationAtRisk": 9800
      },
      "150": {
        "probability": 92,
        "depthM": 0.76,
        "interval90": [
          0.56,
          1.0
        ],
        "confidencePercent": 82,
        "severity": "SEVERE",
        "affectedStructures": 450,
        "populationAtRisk": 20000
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_n",
    "name": "Ghatkopar & LBS Marg (Ward N)",
    "subDistrict": "Pant Nagar / LBS Marg Catchment",
    "ward": "N",
    "gridId": 29800,
    "lng": 72.91,
    "lat": 19.085,
    "elevationM": 5.8,
    "imperviousRatio": 0.86,
    "drainDistanceM": 28,
    "flowAccumulationPercentile": 72,
    "description": "Major commercial and transit corridor: Ghatkopar West LBS Marg, Pant Nagar, and Metro interchange.",
    "citizenAdvice": "LBS Marg near Ghatkopar station accumulates water during heavy bursts. Use Eastern Express Highway.",
    "authorityAction": "Ensure Pant Nagar stormwater nullah is clear of plastic blockage. Keep pumps active at station underpass.",
    "scenarios": {
      "25": {
        "probability": 12,
        "depthM": 0.04,
        "interval90": [
          0.02,
          0.08
        ],
        "confidencePercent": 92,
        "severity": "SAFE",
        "affectedStructures": 18,
        "populationAtRisk": 800
      },
      "50": {
        "probability": 46,
        "depthM": 0.21,
        "interval90": [
          0.11,
          0.33
        ],
        "confidencePercent": 88,
        "severity": "WARNING",
        "affectedStructures": 72,
        "populationAtRisk": 3100
      },
      "100": {
        "probability": 78,
        "depthM": 0.48,
        "interval90": [
          0.33,
          0.65
        ],
        "confidencePercent": 85,
        "severity": "SEVERE",
        "affectedStructures": 210,
        "populationAtRisk": 9400
      },
      "150": {
        "probability": 92,
        "depthM": 0.76,
        "interval90": [
          0.55,
          1.0
        ],
        "confidencePercent": 82,
        "severity": "SEVERE",
        "affectedStructures": 440,
        "populationAtRisk": 19500
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_s",
    "name": "Bhandup & Powai (Ward S)",
    "subDistrict": "Powai Lake Overflow / LBS Marg Basin",
    "ward": "S",
    "gridId": 33000,
    "lng": 72.93,
    "lat": 19.145,
    "elevationM": 9.2,
    "imperviousRatio": 0.76,
    "drainDistanceM": 42,
    "flowAccumulationPercentile": 62,
    "description": "Central suburb basin with Powai Lake catchment, Kanjurmarg, and Bhandup industrial zone.",
    "citizenAdvice": "Watch for Powai Lake overflow along JVLR. LBS Marg Bhandup section has localized pooling.",
    "authorityAction": "Monitor Powai Lake weir discharge level and clear Kanjurmarg box drains.",
    "scenarios": {
      "25": {
        "probability": 8,
        "depthM": 0.03,
        "interval90": [
          0.01,
          0.05
        ],
        "confidencePercent": 94,
        "severity": "SAFE",
        "affectedStructures": 12,
        "populationAtRisk": 500
      },
      "50": {
        "probability": 36,
        "depthM": 0.17,
        "interval90": [
          0.08,
          0.26
        ],
        "confidencePercent": 89,
        "severity": "WARNING",
        "affectedStructures": 50,
        "populationAtRisk": 2200
      },
      "100": {
        "probability": 68,
        "depthM": 0.4,
        "interval90": [
          0.26,
          0.56
        ],
        "confidencePercent": 86,
        "severity": "SEVERE",
        "affectedStructures": 145,
        "populationAtRisk": 6500
      },
      "150": {
        "probability": 86,
        "depthM": 0.65,
        "interval90": [
          0.46,
          0.88
        ],
        "confidencePercent": 83,
        "severity": "SEVERE",
        "affectedStructures": 330,
        "populationAtRisk": 14800
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  },
  {
    "id": "ward_t",
    "name": "Mulund (Ward T)",
    "subDistrict": "Mulund Checknaka / Yogi Hills Basin",
    "ward": "T",
    "gridId": 38000,
    "lng": 72.95,
    "lat": 19.175,
    "elevationM": 11.5,
    "imperviousRatio": 0.7,
    "drainDistanceM": 50,
    "flowAccumulationPercentile": 48,
    "description": "North-eastern boundary of Mumbai bordering Thane along the foot of Yogi Hills.",
    "citizenAdvice": "Generally safe elevated terrain. Minor pooling near Mulund station market and checknaka.",
    "authorityAction": "Ensure Yogi Hills stormwater channels flow cleanly into Thane Creek outfall.",
    "scenarios": {
      "25": {
        "probability": 5,
        "depthM": 0.02,
        "interval90": [
          0.01,
          0.04
        ],
        "confidencePercent": 96,
        "severity": "SAFE",
        "affectedStructures": 6,
        "populationAtRisk": 250
      },
      "50": {
        "probability": 24,
        "depthM": 0.12,
        "interval90": [
          0.06,
          0.19
        ],
        "confidencePercent": 91,
        "severity": "ADVISORY",
        "affectedStructures": 28,
        "populationAtRisk": 1200
      },
      "100": {
        "probability": 52,
        "depthM": 0.3,
        "interval90": [
          0.18,
          0.44
        ],
        "confidencePercent": 87,
        "severity": "WARNING",
        "affectedStructures": 85,
        "populationAtRisk": 3800
      },
      "150": {
        "probability": 75,
        "depthM": 0.5,
        "interval90": [
          0.35,
          0.68
        ],
        "confidencePercent": 84,
        "severity": "SEVERE",
        "affectedStructures": 200,
        "populationAtRisk": 9000
      }
    },
    "explanationFactors": {
      "elevationContribution": 35,
      "drainageContribution": 28,
      "imperviousContribution": 22,
      "rainfallContribution": 15
    }
  }
];

export const getTimelineImpactMetrics = (
  rainfallMmHr: number,
  stepIndex: number
): TimelineImpactMetrics => {
  const stages: TimelineImpactMetrics[] = [
    {
      stage: 'T00',
      stageName: 'T+00m: Pre-Storm Baseline',
      stageDescription: 'Drains flowing with dry-weather baseflow. Gravity outfalls open.',
      alertLevel: 'NORMAL',
      rainfallMmHr: 0,
      drainStressState: 'OPTIMAL',
      stressedDrainsCount: 0,
      overloadedSegmentsCount: 0,
      overflowZonesCount: 0,
      floodedAreaKm2: 0.0,
      affectedStructures: 0,
      populationAtRisk: 0,
      affectedRoadSegments: 0,
      criticalFacilitiesExposed: 0,
      mithiRiverStatus: 'NORMAL',
      runoffMm: 0,
      infiltrationMm: 0,
      totalDrainageM3: 0,
      surfaceStorageM3: 0,
      waterBalanceErrorPercent: 0.02,
    },
    {
      stage: 'T01',
      stageName: 'T+15m: First Flush Inflow',
      stageDescription: 'Storm runoff saturates soil. Surface drains reach 30% hydraulic capacity.',
      alertLevel: 'ADVISORY',
      rainfallMmHr: Math.round(rainfallMmHr * 0.4),
      drainStressState: 'LOADING',
      stressedDrainsCount: 14,
      overloadedSegmentsCount: 2,
      overflowZonesCount: 3,
      floodedAreaKm2: 0.2,
      affectedStructures: 45,
      populationAtRisk: 1800,
      affectedRoadSegments: 4,
      criticalFacilitiesExposed: 0,
      mithiRiverStatus: 'NORMAL',
      runoffMm: Math.round(rainfallMmHr * 0.12),
      infiltrationMm: Math.round(rainfallMmHr * 0.15),
      totalDrainageM3: 42000,
      surfaceStorageM3: 12000,
      waterBalanceErrorPercent: 0.04,
    },
    {
      stage: 'T02',
      stageName: 'T+30m: Drain Capacity Saturation',
      stageDescription: 'Major trunk conduits reach 85% capacity. Low-lying gutters back up.',
      alertLevel: 'FLOOD WATCH',
      rainfallMmHr: Math.round(rainfallMmHr * 0.8),
      drainStressState: 'HIGH LOAD',
      stressedDrainsCount: 48,
      overloadedSegmentsCount: 12,
      overflowZonesCount: 18,
      floodedAreaKm2: 0.8,
      affectedStructures: 180,
      populationAtRisk: 7500,
      affectedRoadSegments: 14,
      criticalFacilitiesExposed: 1,
      mithiRiverStatus: 'ELEVATED',
      runoffMm: Math.round(rainfallMmHr * 0.38),
      infiltrationMm: Math.round(rainfallMmHr * 0.22),
      totalDrainageM3: 145000,
      surfaceStorageM3: 68000,
      waterBalanceErrorPercent: 0.05,
    },
    {
      stage: 'T03',
      stageName: 'T+45m: Pipe Surcharging Peak',
      stageDescription: 'Underpasses and culverts pop into pressure surcharge flow.',
      alertLevel: 'FLOOD WARNING',
      rainfallMmHr: rainfallMmHr,
      drainStressState: 'OVERLOADED',
      stressedDrainsCount: 88,
      overloadedSegmentsCount: 34,
      overflowZonesCount: 42,
      floodedAreaKm2: 1.9,
      affectedStructures: 420,
      populationAtRisk: 18500,
      affectedRoadSegments: 36,
      criticalFacilitiesExposed: 3,
      mithiRiverStatus: 'HIGH STRESS',
      runoffMm: Math.round(rainfallMmHr * 0.68),
      infiltrationMm: Math.round(rainfallMmHr * 0.25),
      totalDrainageM3: 285000,
      surfaceStorageM3: 195000,
      waterBalanceErrorPercent: 0.06,
    },
    {
      stage: 'T04',
      stageName: 'T+60m: Peak Inundation Extent',
      stageDescription: 'Maximum water depth reached across low saucer depressions.',
      alertLevel: 'SEVERE FLOOD EMERGENCY',
      rainfallMmHr: Math.round(rainfallMmHr * 1.05),
      drainStressState: 'SURCHARGING OVERFLOW',
      stressedDrainsCount: 120,
      overloadedSegmentsCount: 52,
      overflowZonesCount: 65,
      floodedAreaKm2: 3.2,
      affectedStructures: 780,
      populationAtRisk: 34000,
      affectedRoadSegments: 58,
      criticalFacilitiesExposed: 5,
      mithiRiverStatus: 'BANKFULL / OVERFLOW',
      runoffMm: Math.round(rainfallMmHr * 0.85),
      infiltrationMm: Math.round(rainfallMmHr * 0.26),
      totalDrainageM3: 390000,
      surfaceStorageM3: 340000,
      waterBalanceErrorPercent: 0.08,
    },
    {
      stage: 'T05',
      stageName: 'T+90m: Slow Gravity Recession',
      stageDescription: 'Rainfall ceases. Gravity drainage slowly discharges as tide recedes.',
      alertLevel: 'FLOOD WATCH',
      rainfallMmHr: Math.round(rainfallMmHr * 0.2),
      drainStressState: 'HIGH LOAD',
      stressedDrainsCount: 65,
      overloadedSegmentsCount: 22,
      overflowZonesCount: 30,
      floodedAreaKm2: 1.8,
      affectedStructures: 390,
      populationAtRisk: 16500,
      affectedRoadSegments: 28,
      criticalFacilitiesExposed: 2,
      mithiRiverStatus: 'HIGH STRESS',
      runoffMm: Math.round(rainfallMmHr * 0.25),
      infiltrationMm: Math.round(rainfallMmHr * 0.28),
      totalDrainageM3: 470000,
      surfaceStorageM3: 180000,
      waterBalanceErrorPercent: 0.06,
    },
    {
      stage: 'T06',
      stageName: 'T+120m: Drainage Clearance',
      stageDescription: 'Major road arteries cleared. Residual ponding localized only in basements.',
      alertLevel: 'ADVISORY',
      rainfallMmHr: 0,
      drainStressState: 'LOADING',
      stressedDrainsCount: 18,
      overloadedSegmentsCount: 4,
      overflowZonesCount: 8,
      floodedAreaKm2: 0.4,
      affectedStructures: 85,
      populationAtRisk: 3600,
      affectedRoadSegments: 8,
      criticalFacilitiesExposed: 0,
      mithiRiverStatus: 'ELEVATED',
      runoffMm: 0,
      infiltrationMm: Math.round(rainfallMmHr * 0.28),
      totalDrainageM3: 540000,
      surfaceStorageM3: 45000,
      waterBalanceErrorPercent: 0.03,
    },
  ];

  const clampedIndex = Math.max(0, Math.min(stepIndex, stages.length - 1));
  return stages[clampedIndex];
};

export function createLocationFromGridFeature(props: any, lng: number, lat: number): MumbaiLocation {
  const gridId = props.grid_id ?? 0;
  const ward = props.ward ? (props.ward + ' Ward') : 'Mumbai Ward';
  const elev = props.elevation_mean ?? 5.0;
  const builtUp = props.built_up_fraction ?? 0.85;
  const drainDist = props.distance_to_drain ?? 45.0;

  return {
    id: 'grid_' + gridId,
    name: 'Cell #' + gridId + ' (' + ward + ')',
    subDistrict: ward + ' Drainage Catchment',
    ward: ward,
    gridId: gridId,
    lng: lng,
    lat: lat,
    elevationM: Math.round(elev * 10) / 10,
    imperviousRatio: Math.round(builtUp * 100) / 100,
    drainDistanceM: Math.round(drainDist),
    flowAccumulationPercentile: Math.min(99, Math.max(20, Math.round(props.flow_accumulation_log ? props.flow_accumulation_log * 12 : 65))),
    description: '100m grid cell in ' + ward + '. Elevation: ' + (Math.round(elev*10)/10) + 'm MSL, Built-up Impervious: ' + Math.round(builtUp*100) + '%, Distance to drain: ' + Math.round(drainDist) + 'm.',
    citizenAdvice: builtUp > 0.8 ? 'High built-up area: Expect rapid road runoff accumulation.' : 'Low built-up area: Infiltration absorbs initial light rainfall.',
    authorityAction: drainDist > 50 ? 'Low local drain density: Ensure portable dewatering pumps are staged nearby.' : 'Drain nearby: Verify catchpit grates are free of debris.',
    explanationFactors: {
      elevationContribution: 35,
      drainageContribution: 28,
      imperviousContribution: 22,
      rainfallContribution: 15,
    },
    scenarios: {
      25: { probability: 15, depthM: 0.04, interval90: [0.01, 0.09], confidencePercent: 90, severity: 'SAFE', affectedStructures: 10, populationAtRisk: 400 },
      50: { probability: 48, depthM: 0.20, interval90: [0.10, 0.32], confidencePercent: 88, severity: 'WARNING', affectedStructures: 60, populationAtRisk: 2500 },
      100: { probability: 82, depthM: 0.45, interval90: [0.30, 0.62], confidencePercent: 85, severity: 'SEVERE', affectedStructures: 220, populationAtRisk: 9500 },
      150: { probability: 94, depthM: 0.82, interval90: [0.60, 1.05], confidencePercent: 82, severity: 'SEVERE', affectedStructures: 520, populationAtRisk: 22000 },
    },
  };
}

// MCGM 24 Administrative Ward Hydrological Catchment Bounding Boxes (with connectivity buffer)
export interface CatchmentBounds {
  minLng: number;
  minLat: number;
  maxLng: number;
  maxLat: number;
}

export const WARD_CATCHMENT_BOUNDS: Record<string, CatchmentBounds> = {
  "A": { minLng: 72.79754, minLat: 18.88673, maxLng: 72.85283, maxLat: 18.95579 },
  "B": { minLng: 72.82575, minLat: 18.94137, maxLng: 72.85514, maxLat: 18.9709 },
  "C": { minLng: 72.81292, minLat: 18.93546, maxLng: 72.83966, maxLat: 18.96787 },
  "D": { minLng: 72.78567, minLat: 18.93315, maxLng: 72.8325, maxLat: 18.98634 },
  "E": { minLng: 72.81259, minLat: 18.95567, maxLng: 72.8619, maxLat: 18.99449 },
  "F/N": { minLng: 72.83681, minLat: 19.00229, maxLng: 72.89101, maxLat: 19.05831 },
  "F/S": { minLng: 72.82689, minLat: 18.97238, maxLng: 72.87569, maxLat: 19.02292 },
  "G/N": { minLng: 72.82208, minLat: 19.0014, maxLng: 72.87419, maxLat: 19.06035 },
  "G/S": { minLng: 72.80213, minLat: 18.97205, maxLng: 72.84236, maxLat: 19.0337 },
  "H/E": { minLng: 72.83315, minLat: 19.04464, maxLng: 72.88219, maxLat: 19.10189 },
  "H/W": { minLng: 72.81151, minLat: 19.0345, maxLng: 72.84882, maxLat: 19.09798 },
  "K/E": { minLng: 72.83682, minLat: 19.07253, maxLng: 72.89444, maxLat: 19.15007 },
  "K/W": { minLng: 72.77466, minLat: 19.07183, maxLng: 72.85616, maxLat: 19.16673 },
  "L": { minLng: 72.86026, minLat: 19.0359, maxLng: 72.91401, maxLat: 19.13532 },
  "M/E": { minLng: 72.88881, minLat: 18.9885, maxLng: 72.96853, maxLat: 19.08174 },
  "M/W": { minLng: 72.87133, minLat: 18.99052, maxLng: 72.91901, maxLat: 19.07969 },
  "N": { minLng: 72.88496, minLat: 19.05359, maxLng: 72.96536, maxLat: 19.12358 },
  "P/N": { minLng: 72.77263, minLat: 19.13448, maxLng: 72.90627, maxLat: 19.23091 },
  "P/S": { minLng: 72.80964, minLat: 19.12331, maxLng: 72.90097, maxLat: 19.18579 },
  "R/C": { minLng: 72.77011, minLat: 19.19569, maxLng: 72.91992, maxLat: 19.27106 },
  "R/N": { minLng: 72.82907, minLat: 19.23088, maxLng: 72.88764, maxLat: 19.27622 },
  "R/S": { minLng: 72.80022, minLat: 19.1791, maxLng: 72.91051, maxLat: 19.22249 },
  "S": { minLng: 72.87833, minLat: 19.09513, maxLng: 72.97932, maxLat: 19.17323 },
  "T": { minLng: 72.87957, minLat: 19.13088, maxLng: 72.98697, maxLat: 19.22358 },
};

export const getLocationCatchmentBounds = (location?: MumbaiLocation | null): CatchmentBounds | null => {
  if (!location) return null;
  const wardClean = location.ward?.replace(/ward/i, '').trim().toUpperCase();
  if (wardClean && WARD_CATCHMENT_BOUNDS[wardClean]) {
    return WARD_CATCHMENT_BOUNDS[wardClean];
  }
  // Geographic fallback based on coordinate envelope with hydrologic connectivity buffer
  return {
    minLng: location.lng - 0.015,
    minLat: location.lat - 0.015,
    maxLng: location.lng + 0.015,
    maxLat: location.lat + 0.015,
  };
};

