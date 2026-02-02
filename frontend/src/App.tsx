import { Toaster } from '@/components/ui/toaster';
import { Dashboard } from '@/components/dashboard/Dashboard';

function App() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-xl font-bold">ITPE Topic Enhancement</h1>
        </div>
      </header>
      <main className="container mx-auto px-4 py-6">
        <Dashboard />
      </main>
      <Toaster />
    </div>
  );
}

export default App;
