import { NextRequest, NextResponse } from "next/server";

const PRIMARY_MODEL = process.env.OPENROUTER_DEFAULT_MODEL || "inclusionai/ling-3.2-flash:free";
const FALLBACK_MODEL = process.env.OPENROUTER_FALLBACK_MODEL || "liquid/lfm-3-1.7b:free";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { mode = "spatial", customPrompt, fieldKey } = body;

    const apiKey = process.env.OPENROUTER_API_KEY;

    if (!apiKey) {
      return NextResponse.json(
        {
          error: "NASA_SERVICE_UNCONFIGURED",
          message: "NASA AI service credentials are not configured on the server.",
        },
        { status: 500 }
      );
    }

    const systemPrompt = `You are a Senior NASA Earth Science & Satellite SAR (Synthetic Aperture Radar) Mission Scientist specializing in Himalayan slope hazards and the historical Kuwari landslide-dammed lake investigation in Bageshwar district, Uttarakhand, India.

INVESTIGATION CONTEXT:
- Discovery window: West 79.75°E, South 30.03°N, East 79.87°E, North 30.15°N. Elevation range ~2,100 m - 3,500 m.
- Satellite: NASA-ISRO SAR (NISAR) L-band, 40 MHz Frequency A, HH+HV dual-polarization, Track 5 Frame 73, Left-looking descending pass.
- Historical Pair: 6 September 2026 vs 30 September 2026 (provisional CRID P05023).
- Finding: Radar backscatter sweep analysis yielded 6 raw sweep-stable pixels on 6-Sept and 12 on 30-Sept. However, after terrain slope filtering and valid-samples mask QC, 0 pixels sustained open water backscatter. No confirmed impounded water body is present. Steep Himalayan relief creates radar layover and shadow.
- Metadata Discrepancy: Granule filename token 'N' expects Near Real-Time Orbit Ephemeris (NOE), but internal HDF5 records Medium Precision Ephemeris (MOE) and Custom attitude.

SCIENTIFIC INTEGRITY RULES:
- Label all AI outputs as "Hypothesis" or "NASA Scientific Interpretation".
- Never claim a confirmed lake shoreline or verified water detection exists.
- Return ONLY valid, parseable JSON matching the requested schema. No markdown fences.`;

    let userPrompt = "";

    if (mode === "metadata_explain") {
      userPrompt = `Explain this specific NISAR satellite acquisition parameter in the context of the Kuwari landslide dam investigation:
Parameter: "${fieldKey}"
${customPrompt ? `Context: ${customPrompt}\n` : ""}

Provide a JSON object with:
{
  "parameter": "${fieldKey}",
  "plain_english": "A 2-sentence clear explanation of what this parameter measures or enforces.",
  "mission_significance": "Why this specific value matters for detecting or ruling out a landslide-dammed lake in Kuwari.",
  "technical_detail": "Physical radar principle (e.g., L-band penetration, incidence geometry, ephemeris accuracy, or mask thresholding)."
}`;
    } else if (mode === "spatial") {
      userPrompt = `Generate rich, actionable NASA geospatial intelligence and target points for the Kuwari discovery zone.
${customPrompt ? `Investigation Focus: ${customPrompt}\n` : ""}

Provide a JSON object with:
{
  "summary": "2-3 sentences synthesizing the terrain, drainage channels, and NISAR radar observation context.",
  "risk_assessment": "Analysis of landslide debris stability, potential river impoundment risk along the stream channel, and monsoon drainage characteristics.",
  "radar_interpretation": "Assessment of NISAR L-band descending track geometry, incidence angles (~37°), and terrain shadow on steep north-facing slopes.",
  "suggested_points": [
    {
      "id": "slug-id",
      "name": "Point Name",
      "category": "Dam & Hazard" or "Hydrology" or "Settlement" or "SAR Geometry" or "Observation",
      "color": "#hex-color (e.g. #ef4444 for hazard, #06b6d4 for hydrology, #10b981 for settlement, #8b5cf6 for SAR geometry, #f59e0b for observation)",
      "coordinates": [longitude_number, latitude_number],
      "elevation": "e.g. 2,380 m",
      "description": "Clear tactical/geographic description.",
      "scientificContext": "Specific SAR backscatter or hydrological relevance."
    }
  ],
  "recommended_actions": [
    "Specific action for high-resolution optical cross-validation",
    "Specific action for ascending track geometry or DEM baseline check"
  ]
}

Note: All suggested point coordinates MUST fall strictly within or immediately adjacent to the discovery window: Longitude between 79.76 and 79.86, Latitude between 30.04 and 30.14. Include 3 to 5 realistic geological/hydrological landmarks.`;
    } else {
      userPrompt = `Generate a comprehensive NASA scientific acquisition synthesis for the NISAR Group D40 24-day pair (6-Sept vs 30-Sept 2026, CRID P05023).
${customPrompt ? `User Focus: ${customPrompt}\n` : ""}

Provide a JSON object with:
{
  "summary": "Detailed technical assessment of the 24-day NISAR acquisition pair over the Bageshwar Kuwari sector.",
  "granule_evaluation": "Explanation of Frequency A 40 MHz dual-polarization (HH+HV) backscatter response over rugged Himalayan topography.",
  "temporal_change": "Physical significance of 6 raw pixels on 6-Sept vs 12 raw pixels on 30-Sept, and why filtering reduced both to 0 valid water candidates.",
  "metadata_anomalies": "Assessment of MOE orbit type and Custom attitude type vs filename token N expectation.",
  "suggested_points": [
    {
      "id": "target-radar-poi",
      "name": "Point Name",
      "category": "SAR Geometry",
      "color": "#8b5cf6",
      "coordinates": [79.815, 30.085],
      "elevation": "2,420 m",
      "description": "Key radar backscatter calibration point in the Kuwari valley.",
      "scientificContext": "Area of high HH/HV ratio variance between 6-Sept and 30-Sept passes."
    }
  ],
  "recommended_actions": [
    "Recommended future NISAR or Sentinel-1 revisit opportunities with target tracks."
  ]
}`;
    }

    // Call AI provider (trying PRIMARY_MODEL, falling back to FALLBACK_MODEL)
    let completionContent = "";
    let lastError: string | null = null;

    for (const modelToTry of [PRIMARY_MODEL, FALLBACK_MODEL]) {
      try {
        const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${apiKey}`,
            "Content-Type": "application/json",
            "HTTP-Referer": "https://rivet.geospatial.nasa.gov",
            "X-Title": "NASA Earth Science RIVET SAR Investigation",
          },
          body: JSON.stringify({
            model: modelToTry,
            messages: [
              { role: "system", content: systemPrompt },
              { role: "user", content: userPrompt },
            ],
            temperature: 0.2,
          }),
        });

        if (response.ok) {
          const completion = await response.json();
          completionContent = completion.choices?.[0]?.message?.content || "";
          if (completionContent) {
            break;
          }
        } else {
          const errText = await response.text();
          lastError = `Status ${response.status}: ${errText.slice(0, 200)}`;
        }
      } catch (e: unknown) {
        lastError = e instanceof Error ? e.message : "Fetch failed";
      }
    }

    if (!completionContent) {
      return NextResponse.json(
        {
          error: "NASA_AI_UNAVAILABLE",
          message: `NASA AI analysis service is temporarily busy. ${lastError || "Please retry in a few moments."}`,
        },
        { status: 502 }
      );
    }

    let parsedData;
    try {
      parsedData = JSON.parse(completionContent);
    } catch {
      // Clean possible markdown code fences
      const cleaned = completionContent
        .replace(/^```(?:json)?\s*/i, "")
        .replace(/\s*```$/i, "")
        .trim();
      try {
        parsedData = JSON.parse(cleaned);
      } catch {
        // Fallback: extract JSON substring if wrapped in prose
        const match = cleaned.match(/\{[\s\S]*\}/);
        if (match) {
          parsedData = JSON.parse(match[0]);
        } else {
          return NextResponse.json(
            {
              error: "PARSE_ERROR",
              message: "NASA AI returned response in non-JSON format.",
              raw: completionContent,
            },
            { status: 500 }
          );
        }
      }
    }

    return NextResponse.json({
      success: true,
      provider: "NASA Earth Science Mission Intelligence",
      timestamp: new Date().toISOString(),
      data: parsedData,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json({ error: "INTERNAL_ERROR", message }, { status: 500 });
  }
}
