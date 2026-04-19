export interface FlashCardData {
  id: string;
  topic: string;
  information_to_be_shared: string;
}

interface FlashCardProps {
  card: FlashCardData;
}

const routeConfig = {
  BlockRoute: "Block Route",
  DiningHallTimings: "Dining Hall Timings or Cafeteria Timing",
};
export default function FlashCard({ card }: FlashCardProps) {
  const renderInformation = (topic: string, str: string) => {
    if (Object.keys(routeConfig).includes(topic)) {
      return <p>{routeConfig[topic as keyof typeof routeConfig]}</p>;
    }
    return <p>{str}</p>;
  };
  return (
    <div className="w-full max-w-md mx-auto cursor-pointer">
      <div key="front" className="bg-white text-black p-6 rounded-lg shadow-lg">
        <p className="text-lg font-semibold mb-2">{card.topic}</p>
        <p>{renderInformation(card.topic, card.information_to_be_shared)}</p>
      </div>
    </div>
  );
}
