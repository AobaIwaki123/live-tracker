import { useState } from "react";
import { X, Plus, Info, Palette } from "lucide-react";

interface ArtistCreatePayload {
  name: string;
  display_name: string;
  theme_color: string;
  image_url: string;
  base_url: string;
}

interface ArtistCreateFormProps {
  onSave: (data: ArtistCreatePayload) => void;
  onCancel: () => void;
}

export default function ArtistCreateForm({ onSave, onCancel }: ArtistCreateFormProps) {
  const [formData, setFormData] = useState<ArtistCreatePayload>({
    name: "",
    display_name: "",
    theme_color: "#888888",
    image_url: "",
    base_url: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 z-[150] flex items-center justify-center bg-white/60 backdrop-blur-xl p-4 animate-in fade-in duration-500">
      <div className="w-full max-w-xl overflow-hidden rounded-[3.5rem] bg-white shadow-[0_32px_64px_-16px_rgba(109,40,217,0.2)] border border-purple-100 animate-in zoom-in-95 duration-300">
        <div className="flex items-center justify-between border-b border-purple-50 p-8 px-10 bg-gradient-to-r from-purple-50/50 to-transparent">
          <div className="flex items-center gap-5">
            <div 
              className="h-10 w-10 rounded-2xl shadow-lg rotate-3" 
              style={{ backgroundColor: formData.theme_color }}
            />
            <div>
              <h2 className="text-3xl font-black tracking-tighter text-slate-900">Add Artist</h2>
              <p className="text-sm font-bold text-purple-600/60 uppercase tracking-widest">New Registration</p>
            </div>
          </div>
          <button 
            onClick={onCancel}
            className="rounded-2xl p-3 text-slate-400 hover:bg-purple-50 hover:text-purple-600 transition-all active:scale-90"
          >
            <X className="h-7 w-7" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-10 space-y-7 max-h-[75vh] overflow-y-auto custom-scrollbar">
          {/* ID (Name) */}
          <div className="group space-y-3">
            <label className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.2em] text-slate-400 ml-1 group-focus-within:text-purple-600 transition-colors">
              Internal ID
              <Info className="h-3.5 w-3.5" />
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "") })}
              className="w-full rounded-[1.25rem] bg-slate-50 px-6 py-4 text-xl font-mono border-2 border-slate-100 focus:border-purple-500 focus:bg-white focus:outline-none transition-all placeholder:text-slate-300 shadow-sm"
              placeholder="jj"
            />
            <p className="text-[10px] text-slate-400 font-bold ml-1 uppercase tracking-tight">Alphanumeric only (e.g. avam, hnz)</p>
          </div>

          {/* Display Name */}
          <div className="group space-y-3">
            <label className="text-xs font-black uppercase tracking-[0.2em] text-slate-400 ml-1 group-focus-within:text-purple-600 transition-colors">
              Display Name
            </label>
            <input
              type="text"
              required
              value={formData.display_name}
              onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
              className="w-full rounded-[1.25rem] bg-slate-50 px-6 py-4 text-xl font-bold border-2 border-slate-100 focus:border-purple-500 focus:bg-white focus:outline-none transition-all placeholder:text-slate-300 shadow-sm"
              placeholder="Juice=Juice"
            />
          </div>

          {/* Theme Color */}
          <div className="group space-y-3">
            <label className="text-xs font-black uppercase tracking-[0.2em] text-slate-400 ml-1 group-focus-within:text-purple-600 transition-colors">
              Theme Color
            </label>
            <div className="flex items-center gap-5 p-2 pr-6 rounded-[1.5rem] bg-slate-50 border-2 border-slate-100 group-focus-within:border-purple-500 group-focus-within:bg-white transition-all shadow-sm">
              <div className="relative h-16 w-16 shrink-0 group/picker">
                <input
                  type="color"
                  value={formData.theme_color}
                  onChange={(e) => setFormData({ ...formData, theme_color: e.target.value })}
                  className="absolute inset-0 opacity-0 w-full h-full cursor-pointer z-10"
                />
                <div 
                  className="absolute inset-0 rounded-2xl shadow-inner border-4 border-white transition-transform group-hover/picker:scale-105 group-active/picker:scale-95 flex items-center justify-center overflow-hidden"
                  style={{ backgroundColor: formData.theme_color }}
                >
                  <div className="bg-white/20 backdrop-blur-md p-2 rounded-full opacity-0 group-hover/picker:opacity-100 transition-opacity">
                    <Plus className="h-5 w-5 text-white" />
                  </div>
                </div>
              </div>
              
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-400">
                  <Palette className="h-3 w-3" />
                  Click to pick or type hex
                </div>
                <input
                  type="text"
                  value={formData.theme_color}
                  onChange={(e) => setFormData({ ...formData, theme_color: e.target.value })}
                  className="w-full bg-transparent text-2xl font-mono focus:outline-none uppercase text-slate-700"
                  placeholder="#888888"
                  pattern="^#[0-9A-Fa-f]{6}$"
                />
              </div>
            </div>
          </div>

          {/* Image URL */}
          <div className="group space-y-3">
            <label className="text-xs font-black uppercase tracking-[0.2em] text-slate-400 ml-1 group-focus-within:text-purple-600 transition-colors">
              Image URL
            </label>
            <input
              type="text"
              required
              value={formData.image_url}
              onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
              className="w-full rounded-[1.25rem] bg-slate-50 px-6 py-4 text-lg font-medium border-2 border-slate-100 focus:border-purple-500 focus:bg-white focus:outline-none transition-all placeholder:text-slate-300 shadow-sm"
              placeholder="https://images.example.com/artist.jpg"
            />
          </div>

          {/* Base URL */}
          <div className="group space-y-3">
            <label className="text-xs font-black uppercase tracking-[0.2em] text-slate-400 ml-1 group-focus-within:text-purple-600 transition-colors">
              Schedule Page URL
            </label>
            <input
              type="text"
              required
              value={formData.base_url}
              onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
              className="w-full rounded-[1.25rem] bg-slate-50 px-6 py-4 text-lg font-medium border-2 border-slate-100 focus:border-purple-500 focus:bg-white focus:outline-none transition-all placeholder:text-slate-300 shadow-sm"
              placeholder="https://artist-site.com/schedule"
            />
          </div>

          <div className="pt-6 flex gap-4">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 rounded-[1.5rem] border-2 border-slate-100 px-8 py-5 text-lg font-black text-slate-400 transition-all hover:bg-slate-50 hover:text-slate-600 active:scale-95"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-[2] flex items-center justify-center gap-3 rounded-[1.5rem] bg-gradient-to-r from-violet-600 to-purple-600 px-8 py-5 text-lg font-black text-white shadow-xl shadow-purple-200 transition-all hover:scale-[1.02] hover:shadow-purple-300 active:scale-95"
            >
              <Plus className="h-6 w-6" />
              Add Artist
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
