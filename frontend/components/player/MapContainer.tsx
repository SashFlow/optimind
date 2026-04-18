import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "../ui/dialog";
import Image from "next/image";

export function MapContainer(props: { show: boolean; onClose: () => void }) {
  return (
    <Dialog open={props.show} onOpenChange={props.onClose}>
      <DialogContent className="bg-gray-800 border-gray-700 text-white max-w-md">
        <DialogHeader className="flex flex-row items-center justify-between">
          <DialogTitle className="flex items-center gap-2 text-white">
            <span>LDA Map</span>
          </DialogTitle>
          <DialogClose className="text-white hover:text-gray-300" />
        </DialogHeader>

        <div className="flex flex-col items-center gap-6 py-4">
          {/* Driver Profile */}
          <div className="flex flex-col items-center gap-4">
            {/* Driver Information */}
            <div className="flex flex-col items-center gap-4 w-full">
              <Image src="/map.png" alt="LDA Map" width={512} height={512} />
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
