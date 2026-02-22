import { NextRequest, NextResponse } from "next/server";
import { execSync } from "child_process";
import { writeFileSync, mkdirSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { randomUUID } from "crypto";

export async function POST(req: NextRequest) {
  try {
    const { routine_yaml, udf_source, input } = await req.json();
    if (!routine_yaml) {
      return NextResponse.json({ error: "Missing routine_yaml" }, { status: 400 });
    }

    const workDir = join(tmpdir(), `em-run-${randomUUID()}`);
    mkdirSync(workDir, { recursive: true });

    writeFileSync(join(workDir, "routine.yaml"), routine_yaml);
    if (udf_source) {
      writeFileSync(join(workDir, "udf.py"), udf_source);
    }

    const inputFile = join(workDir, "input.json");
    writeFileSync(inputFile, JSON.stringify(input || {}));

    const stdout = execSync(
      `em run "${workDir}" --input "${inputFile}" --json`,
      { timeout: 30000, encoding: "utf-8" }
    );

    const result = JSON.parse(stdout);
    return NextResponse.json(result);
  } catch (err: any) {
    return NextResponse.json(
      { error: err.stderr || err.message || "Run failed" },
      { status: 500 }
    );
  }
}
