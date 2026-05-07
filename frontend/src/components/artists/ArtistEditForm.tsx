import { useState } from "react";
import { X, Save, Info } from "lucide-react";

interface Artist {
  name: string;
  display_name: string;
  theme_color: string;
  image_url: string;
  base_url: string;
}

interface ArtistEditFormProps {
  artist: Artist;
  onSave: (data: Omit<Artist, "name">) => void;
  onCancel: () => void;
}

export default function ArtistEditForm({ artist, onSave, onCancel }: ArtistEditFormProps) {
  const [formData, setFormData] = useState({
    display_name: artist.display_name || "",
    theme_color: artist.theme_color || "#888888",
    image_url: artist.image_url || "",
    base_url: artist.base_url || "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 z-[150] flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
      <div className="w-full max-w-xl overflow-hidden rounded-[3rem] bg-card shadow-2xl border border-border animate-in zoom-in-95 duration-300">
        <div className="flex items-center justify-between border-b border-border p-8 px-10">
          <div className="flex items-center gap-4">
            <div 
              className="h-4 w-4 rounded-full shadow-lg" 
              style={{ backgroundColor: formData.theme_color }}
            />
            <h2 className="text-3xl font-black tracking-tighter">Edit Artist</h2>
          </div>
          <button 
            onClick={onCancel}
            className="rounded-full p-2 text-muted-foreground hover:bg-muted transition-colors"
          >
            <X className="h-8 w-8" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-10 space-y-8">
          {/* ID (Read Only) */}
          <div className="space-y-3">
            <label className="flex items-center gap-2 text-sm font-black uppercase tracking-widest text-muted-foreground ml-1">
              Internal ID (Name)
              <Info className="h-3.5 w-3.5" />
            </label>
            <div className="rounded-2xl bg-muted px-6 py-4 font-mono text-lg text-muted-foreground border border-border/50">
              {artist.name}
            </div>
            <p className="text-xs text-muted-foreground/60 italic ml-1">System identifier used for filenames and database.</p>
          </div>

          {/* Display Name */}
          <div className="space-y-3">
            <label className="text-sm font-black uppercase tracking-widest text-muted-foreground ml-1">
              Display Name
            </label>
            <input
              type="text"
              required
              value={formData.display_name}
              onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
              className="w-full rounded-2xl bg-muted px-6 py-4 text-xl font-bold border-2 border-transparent focus:border-primary focus:outline-none transition-all placeholder:text-muted-foreground/40"
              placeholder="e.g. Juice=Juice"
            />
          </div>

          {/* Theme Color */}
          <div className="space-y-3">
            <label className="text-sm font-black uppercase tracking-widest text-muted-foreground ml-1">
              Theme Color
            </label>
            <div className="flex gap-4">
              <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-2xl border-2 border-border/50 shadow-inner">
                <input
                  type="color"
                  value={formData.theme_color}
                  onChange={(e) => setFormData({ ...formData, theme_color: e.target.value })}
                  className="absolute inset-[-8px] h-[calc(100%+16px)] w-[calc(100%+16px)] cursor-pointer"
                />
              </div>
              <input
                type="text"
                value={formData.theme_color}
                onChange={(e) => setFormData({ ...formData, theme_color: e.target.value })}
                className="flex-1 rounded-2xl bg-muted px-6 py-4 text-xl font-mono border-2 border-transparent focus:border-primary focus:outline-none transition-all uppercase"
                placeholder="#000000"
                pattern="^#[0-9A-Fa-f]{6}$"
              />
            </div>
          </div>

          {/* Image URL */}
          <div className="space-y-3">
            <label className="text-sm font-black uppercase tracking-widest text-muted-foreground ml-1">
              Image URL
            </label>
            <input
              type="text"
              required
              value={formData.image_url}
              onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
              className="w-full rounded-2xl bg-muted px-6 py-4 text-lg font-medium border-2 border-transparent focus:border-primary focus:outline-none transition-all"
              placeholder="https://..."
            />
          </div>

          {/* Base URL */}
          <div className="space-y-3">
            <label className="text-sm font-black uppercase tracking-widest text-muted-foreground ml-1">
              Schedule Page URL (Base URL)
            </label>
            <input
              type="text"
              required
              value={formData.base_url}
              onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
              className="w-full rounded-2xl bg-muted px-6 py-4 text-lg font-medium border-2 border-transparent focus:border-primary focus:outline-none transition-all"
              placeholder="https://..."
            />
          </div>

          <div className="pt-6 flex gap-4">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 rounded-2xl border-2 border-border px-8 py-5 text-lg font-black transition-all hover:bg-muted active:scale-95"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-[2] flex items-center justify-center gap-3 rounded-2xl bg-primary px-8 py-5 text-lg font-black text-primary-foreground shadow-xl shadow-primary/20 transition-all hover:scale-[1.02] active:scale-95"
            >
              <Save className="h-6 w-6" />
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
