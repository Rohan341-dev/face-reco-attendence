import { useEffect, useState } from "react"
import { NavigationContainer } from "@react-navigation/native"
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs"
import { createNativeStackNavigator } from "@react-navigation/native-stack"
import { StatusBar } from "expo-status-bar"

import { getAccess } from "./lib/api"
import { HomeScreen } from "./screens/HomeScreen"
import { HistoryScreen } from "./screens/HistoryScreen"
import { LoginScreen } from "./screens/LoginScreen"

const Stack = createNativeStackNavigator()
const Tabs = createBottomTabNavigator()

function Authenticated({ onSignOut }: { onSignOut: () => void }) {
  return (
    <Tabs.Navigator screenOptions={{ headerStyle: { backgroundColor: "#0f1727" }, headerTintColor: "#e6edf7" }}>
      <Tabs.Screen name="Today" options={{ headerShown: false }}>
        {() => <HomeScreen onSignOut={onSignOut} />}
      </Tabs.Screen>
      <Tabs.Screen name="History" component={HistoryScreen} />
    </Tabs.Navigator>
  )
}

export default function App() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)

  useEffect(() => {
    void getAccess().then((token) => setAuthenticated(Boolean(token)))
  }, [])

  if (authenticated === null) return null

  return (
    <NavigationContainer>
      <StatusBar style="light" />
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {authenticated ? (
          <Stack.Screen name="App">
            {() => <Authenticated onSignOut={() => setAuthenticated(false)} />}
          </Stack.Screen>
        ) : (
          <Stack.Screen name="Login">
            {() => <LoginScreen onSuccess={() => setAuthenticated(true)} />}
          </Stack.Screen>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  )
}
