/* PLACEHOLDER -- replace with the real TradingView lightweight-charts standalone
   build (https://github.com/tradingview/lightweight-charts, file
   lightweight-charts.standalone.production.js) on a machine with internet, then
   commit it here. This stub only lets the server boot and the smoke tests pass;
   it does NOT render real charts. */
window.LightweightCharts = window.LightweightCharts || {
  createChart: function () {
    console.error("lightweight-charts placeholder loaded -- vendor the real file to render charts");
    var series = function () { return { setData: function () {} }; };
    return {
      addCandlestickSeries: series,
      addHistogramSeries: series,
      addLineSeries: series
    };
  }
};
