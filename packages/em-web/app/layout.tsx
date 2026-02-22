export const metadata = {
  title: "Executable Memory — Demo",
  description: "Convert agent traces into deterministic routines",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#0a0a0a", color: "#ededed" }}>
        {children}
      </body>
    </html>
  );
}
