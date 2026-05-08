declare module 'react-apexcharts' {
  import { Component } from 'react'

  interface ApexOptions {
    chart?: {
      type?: string
      height?: number | string
      toolbar?: { show?: boolean }
      background?: string
      zoom?: { enabled?: boolean }
    }
    theme?: { mode?: 'light' | 'dark' }
    plotOptions?: {
      candlestick?: {
        colors?: { upward?: string; downward?: string }
        wick?: { useFillColor?: boolean }
      }
    }
    grid?: { borderColor?: string }
    xaxis?: {
      type?: string
      labels?: { style?: { colors?: string } }
      axisBorder?: { color?: string }
      axisTicks?: { color?: string }
    }
    yaxis?: {
      tooltip?: { enabled?: boolean }
      labels?: {
        style?: { colors?: string }
        formatter?: (val: number) => string
      }
    }
    tooltip?: { theme?: string; style?: { fontSize?: string } }
  }

  interface SeriesItem {
    data: Array<{
      x: Date
      y: [number, number, number, number]
    }>
  }

  interface Props {
    options: ApexOptions
    series: SeriesItem[]
    type?: string
    height?: number | string
    width?: number | string
  }

  export default class Chart extends Component<Props> {}
}
