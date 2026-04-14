from google.adk.agents import Agent

# Simple tool
def measure_temperature_tool(location: str) -> dict:
    return {"status": "success", "location": location, "temperature": "25°C"}

# Root agent
root_agent = Agent(
    name="simple_agent",
    model="gemini-2.5-flash",
    description="A simple assistant that can measure temperature.",
    tools=[measure_temperature_tool],
)