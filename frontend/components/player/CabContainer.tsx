import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "../ui/dialog";

export function CabContainer(props: { show: boolean; onClose: () => void }) {
  const drivers = [
    { name: "Kamlesh", phone: "+91-9611112036" },
    { name: "Firoz", phone: "+91-7775031110" },
    { name: "Vishnu", phone: "+91-9579793318" },
  ];

  return (
    <Dialog open={props.show} onOpenChange={props.onClose}>
      <DialogContent className="bg-gray-800 border-gray-700 text-white max-w-md">
        <DialogHeader className="flex flex-row items-center justify-between">
          <DialogTitle className="flex items-center gap-2 text-white">
            <span className="text-2xl">🚕</span>
            <span>Your Cab Driver</span>
          </DialogTitle>
          <DialogClose className="text-white hover:text-gray-300" />
        </DialogHeader>

        <div className="flex flex-col items-center gap-6 py-4">
          {/* Driver Profile */}
          <div className="flex flex-col items-center gap-4">
            {/* Driver Information */}
            <div className="flex flex-col items-center gap-4 w-full">
              {drivers.map((driver, index) => (
                <div key={index} className="flex flex-col items-center gap-1">
                  <span className="text-blue-400 font-medium">
                    {driver.name}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-white">Phone:</span>
                    <span className="text-white">{driver.phone}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
