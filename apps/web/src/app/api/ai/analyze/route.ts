import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { apiKey: clientApiKey, model = "google/gemini-2.0-flash-001", mode = "spatial", customPrompt } = body;

    const apiKey = clientApiKey || process.env.OPENROUTER_API_KEY;

    if (!apiKey) {
      return NextResponse.json(
        {
          error: "API_KEY_REQUIRED",
          message: "Please provide an OpenRouter API key to enable live AI intelligence generation.",
        },
        { status: 400 }
      );
    }

    const systemPrompt = `You are a Principal Geospatial Intelligence Scientist and Satellite SAR (Synthetic Aperture Radar) Analyst specializing in Himalayan slope hazards and the historical Kuwari landslide-dammed lake investigation in Bageshwar district, Uttarakhand, India.

INVESTIGATION CONTEXT:
- Discovery window: West 79.75°E, South 30.03°N, East 79.87°E, North 30.15°N.
- Satellite: NASA-ISRO SAR (NISAR) L-band, 40 MHz Frequency A, HH+HV dual-polarization, Track 5 Frame 73, Left-looking descending pass.
- Historical Pair: 6 September 2026 vs 30 September 2026 (provisional CRID P05023).
- Finding: Radar backscatter sweep analysis yielded 0 sustained filtered open water pixels. No confirmed water body is present. High mountain relief creates radar layover and shadow.

RULES:
- Maintain strict scientific integrity. Label all conclusions as "Hypothesis" or "AI Interpretation".
- Never claim a confirmed water detection or surveyed lake outline exists.
- Return ONLY valid, parseable JSON matching the requested schema. No markdown code fences.`;

    const userPrompt = mode === "spatial"
      ? `Generate rich, actionable geospatial intelligence for the Kuwari discovery zone.
${customPrompt ? `User Focus: ${customPrompt}\n` : ""}
Provide a JSON object with:
{
  "summary": "2-3 sentences synthesizing the terrain, drainage, and radar observation context.",
  "risk_assessment": "Analysis of landslide debris stability, river impoundment risk, and monsoon drainage characteristics.",
  "radar_interpretation": "Assessment of NISAR L-band descending track geometry, incidence angles (~37°), and terrain shadow on north-facing slopes.",
  "suggested_points": [
    {
      "id": "slug-string",
      "name": "Point Name",
      "category": "Dam & Hazard" | "Hydrology" | "Settlement" | "SAR Geometry" | "Observation",
      "color": "#hex-color",
      "coordinates": [longitude_number, latitude_number],
      "elevation": "e.g. 2,380 m",
      "description": "Clear tactical/geographic description.",
      "scientificContext": "Specific SAR or hydrological relevance."
    }
  ],
  "recommended_actions": [
    "Action 1 for satellite validation or optical recheck",
    "Action 2 for terrain geometry verification"
  ]
}

Note: All suggested point coordinates MUST fall strictly within or immediately adjacent to the discovery window: Longitude between 79.76 and 79.86, Latitude between 30.04 and 30.14.`
      : `Generate scientific acquisition analysis for NISAR Group D40 (6-Sept vs 30-Sept 2026, CRID P05023).
${customPrompt ? `User Focus: ${customPrompt}\n` : ""}
Provide a JSON object with:
{
  "summary": "Detailed technical assessment of the 24-day NISAR acquisition pair.",
  "granule_evaluation": "Explanation of Frequency A 40 MHz dual-polarization backscatter response over rugged terrain.",
  "temporal_change": "Significance of 6 raw pixels on 6-Sept vs 12 raw pixels on 30-Sept with 0 filtered candidates.",
  "metadata_anomalies": "Assessment of MOE orbit type and Custom attitude type vs filename token N expectation.",
  "next_satellite_passes": [
    "Recommended future NISAR or Sentinel-1 revisit opportunities with target tracks."
  ]
}`;

    const openRouterRes = await fetch("https://openrouter.ai/api/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://rivet.geospatial.local",
        "X-Title": "RIVET SAR Investigation",
      },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt },
        ],
        temperature: 0.3,
        response_format: { type: "json_object" },
      }),
    });

    if (!openRouterRes.ok) {
      const errText = await openRouterRes.text();
      let parsedErr = errText;
      try {
        const j = JSON.parse(errText);
        parsedErr = j.error?.message || errText;
      } catch {}
      return NextResponse.json(
        { error: "OPENROUTER_ERROR", message: `OpenRouter error (${openRouterRes.status}): ${parsedErr}` },
        { status: openRouterRes.status }
      );
    }

    const completion = await openRouterRes.json();
    const content = completion.choices?.[0]?.message?.content;

    let parsedData;
    try {
      parsedData = JSON.parse(content);
    } catch {
      // Fallback in case response included markdown formatting
      const cleaned = content.replace(/^```json\s*/, "").replace(/\s*```$/, "");
      parsedData = JSON.parse(cleaned);
    }

    return NextResponse.json({
      success: true,
      model,
      timestamp: new Date().toISOString(),
      data: parsedData,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json({ error: "INTERNAL_ERROR", message }, { status: 500 });
  }
}
