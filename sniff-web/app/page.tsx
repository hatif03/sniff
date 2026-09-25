import HeroSection from "@/components/HeroSection";
import ProblemSection from "@/components/ProblemSection";
import HowItWorksSection from "@/components/HowItWorksSection";
import ReplaySection from "@/components/ReplaySection";
import DifferentiatorsSection from "@/components/DifferentiatorsSection";
import ArchitectureSection from "@/components/ArchitectureSection";
import FooterCTA from "@/components/FooterCTA";

export default function Home() {
  return (
    <main className="min-h-screen">
      <HeroSection />
      <ProblemSection />
      <HowItWorksSection />
      <ReplaySection />
      <DifferentiatorsSection />
      <ArchitectureSection />
      <FooterCTA />
    </main>
  );
}
