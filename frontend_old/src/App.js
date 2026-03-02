import { useState } from "react";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export default function AIRecommendationUI() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);

  const search = async () => {
    const res = await fetch("http://127.0.0.1:8000/semantic-search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: 5 })
    });
    const data = await res.json();
    setResults(data.results || []);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 to-slate-900 text-white p-10">
      <motion.h1 initial={{opacity:0,y:-20}} animate={{opacity:1,y:0}} className="text-4xl font-bold mb-6 text-center">
        AI Recommendation Platform
      </motion.h1>

      <div className="max-w-2xl mx-auto flex gap-2">
        <Input
          placeholder="Search assessments, skills, roles..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="bg-slate-800 border-slate-700 text-white"
        />
        <Button onClick={search} className="rounded-xl">Search</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-10">
        {results.map((r, i) => (
          <motion.div key={i} initial={{opacity:0,scale:0.9}} animate={{opacity:1,scale:1}} transition={{delay:i*0.05}}>
            <Card className="bg-slate-800 border-slate-700 rounded-2xl shadow-xl">
              <CardContent className="p-5">
                <h2 className="text-lg font-semibold mb-2">{r.name}</h2>
                <p className="text-sm text-slate-300 mb-2">{r.job_family}</p>
                <div className="flex flex-wrap gap-1 mb-2">
                  {r.test_type?.map((t,idx)=>(<Badge key={idx}>{t}</Badge>))}
                </div>
                <p className="text-xs text-slate-400">Confidence: {r.confidence}</p>
                <p className="text-xs text-slate-400">Score: {r.score.toFixed(3)}</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
