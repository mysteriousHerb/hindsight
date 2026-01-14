import { NextResponse } from "next/server";
import { lowLevelClient } from "@/lib/hindsight-client";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ bankId: string; modelId: string }> }
) {
  try {
    const { bankId, modelId } = await params;

    if (!bankId) {
      return NextResponse.json({ error: "bank_id is required" }, { status: 400 });
    }

    if (!modelId) {
      return NextResponse.json({ error: "model_id is required" }, { status: 400 });
    }

    // Call the API endpoint directly since SDK may not be regenerated yet
    const response = await lowLevelClient.POST(
      "/v1/default/banks/{bank_id}/mental-models/{model_id}/generate",
      {
        params: { path: { bank_id: bankId, model_id: modelId } },
      }
    );

    if (response.error) {
      console.error("API error generating mental model:", response.error);
      return NextResponse.json({ error: "Failed to generate mental model" }, { status: 500 });
    }

    return NextResponse.json(response.data, { status: 200 });
  } catch (error) {
    console.error("Error generating mental model:", error);
    return NextResponse.json({ error: "Failed to generate mental model" }, { status: 500 });
  }
}
