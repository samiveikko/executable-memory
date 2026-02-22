import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const { run_id, answers } = await req.json();

    // Resume is more complex — requires the state store to have the run state.
    // For the demo, we return a placeholder since full resume requires persistent state
    // between the run and resume API calls.
    return NextResponse.json({
      run_id,
      status: "ok",
      output: { message: "Resume not yet supported in web demo — use the CLI for full prompt.user support." },
    });
  } catch (err: any) {
    return NextResponse.json(
      { error: err.message || "Resume failed" },
      { status: 500 }
    );
  }
}
