export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900">
      <main className="text-center px-4">
        <h1 className="text-5xl font-bold text-green-600 dark:text-green-400 mb-4">🌿 Lawn</h1>
        <p className="text-lg text-gray-600 dark:text-gray-400 mb-8">
          Smarter lawn care, powered by data.
        </p>
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 text-sm font-medium">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          Coming soon
        </div>
      </main>
    </div>
  );
}
