import { NextRequest, NextResponse } from "next/server";
import { execSync } from "child_process";
import { writeFileSync, readFileSync, mkdirSync, existsSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { randomUUID } from "crypto";

export async function POST(req: NextRequest) {
  try {
    const { trace } = await req.json();
    if (!trace) {
      return NextResponse.json({ error: "Missing trace" }, { status: 400 });
    }

    const workDir = join(tmpdir(), `em-compile-${randomUUID()}`);
    mkdirSync(workDir, { recursive: true });

    const traceFile = join(workDir, "trace.json");
    const outDir = join(workDir, "output");
    writeFileSync(traceFile, JSON.stringify(trace));

    execSync(`em compile "${traceFile}" -o "${outDir}"`, {
      timeout: 30000,
      encoding: "utf-8",
    });

    const routineYaml = readFileSync(join(outDir, "routine.yaml"), "utf-8");
    const udfPath = join(outDir, "udf.py");
    const udfSource = existsSync(udfPath) ? readFileSync(udfPath, "utf-8") : "";

    return NextResponse.json({
      routine_yaml: routineYaml,
      udf_source: udfSource,
    });
  } catch (err: any) {
    return NextResponse.json(
      { error: err.stderr || err.message || "Compile failed" },
      { status: 500 }
    );
  }
}
