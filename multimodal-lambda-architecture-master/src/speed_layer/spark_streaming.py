from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, avg, stddev, to_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType

from pyspark.sql import DataFrame

CASSANDRA_KEYSPACE = "landcover"
REALTIME_TABLE = "realtime_ndvi_by_class"
ANOMALY_TABLE = "anomaly_alerts"

schema = StructType([
    StructField("image_id", StringType(), True),
    StructField("class_name", StringType(), True),
    StructField("ndvi_mean", DoubleType(), True),
    StructField("ndvi_std", DoubleType(), True),
    StructField("ndvi_min", DoubleType(), True),
    StructField("ndvi_max", DoubleType(), True),
    StructField("vegetation_index", StringType(), True),
    StructField("red_mean", DoubleType(), True),
    StructField("green_mean", DoubleType(), True),
    StructField("blue_mean", DoubleType(), True),
    StructField("nir_mean", DoubleType(), True),
    StructField("brightness_mean", DoubleType(), True),
    StructField("timestamp", TimestampType(), True),
])


def write_to_cassandra(df: DataFrame, table: str):
    df.write \
      .format("org.apache.spark.sql.cassandra") \
      .mode("append") \
      .options(table=table, keyspace=CASSANDRA_KEYSPACE) \
      .save()


def main():
    spark = SparkSession.builder \
        .appName("SpeedLayer") \
        .config("spark.cassandra.connection.host", "cassandra") \
        .getOrCreate()

    raw = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:9092") \
        .option("subscribe", "image-events") \
        .option("startingOffsets", "latest") \
        .load()

    events = raw.select(from_json(col("value").cast("string"), schema).alias("json")).select("json.*") \
                 .withColumn("timestamp", to_timestamp(col("timestamp")))

    # Rolling NDVI by class
    ndvi_by_class = events \
        .withWatermark("timestamp", "2 minutes") \
        .groupBy(
            window(col("timestamp"), "5 minutes"),
            col("class_name")
        ).agg(
            avg("ndvi_mean").alias("ndvi_avg"),
            stddev("ndvi_mean").alias("ndvi_stddev")
        ).select(
            col("class_name"),
            col("ndvi_avg"),
            col("ndvi_stddev"),
        )

    anomalies = events \
        .filter((col("ndvi_mean").isNotNull()) & (col("ndvi_std").isNotNull()) & (col("ndvi_std") > 0)) \
        .filter((col("ndvi_min") < (col("ndvi_mean") - 2 * col("ndvi_std"))) | (col("ndvi_max") > (col("ndvi_mean") + 2 * col("ndvi_std")))) \
        .select("image_id", "class_name", "ndvi_mean", "ndvi_min", "ndvi_max", "timestamp")

    ndvi_query = ndvi_by_class.writeStream \
        .foreachBatch(lambda df, _: write_to_cassandra(df, REALTIME_TABLE)) \
        .outputMode("update") \
        .option("checkpointLocation", "/tmp/spark_speed_ndvi_ckpt") \
        .start()

    anomaly_query = anomalies.writeStream \
        .foreachBatch(lambda df, _: write_to_cassandra(df, ANOMALY_TABLE)) \
        .outputMode("append") \
        .option("checkpointLocation", "/tmp/spark_speed_anomaly_ckpt") \
        .start()

    ndvi_query.awaitTermination()
    anomaly_query.awaitTermination()


if __name__ == "__main__":
    main()
