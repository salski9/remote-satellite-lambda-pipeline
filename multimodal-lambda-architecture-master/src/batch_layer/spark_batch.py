from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, stddev, max as spark_max, min as spark_min, count

RAW_HDFS = "hdfs://namenode:8020/raw/landcover"
CURATED_HDFS = "hdfs://namenode:8020/curated/landcover_stats"
LOCAL_RAW = "/opt/spark/data/data"


def main():
    spark = SparkSession.builder.appName("BatchLayer").enableHiveSupport().getOrCreate()

    def read_csv(path):
        return spark.read.option("header", True).csv(path)

    try:
        images = read_csv(f"{RAW_HDFS}/images.csv")
        classes = read_csv(f"{RAW_HDFS}/classes.csv")
        ndvi = read_csv(f"{RAW_HDFS}/ndvi_stats.csv")
        spectral = read_csv(f"{RAW_HDFS}/spectral_data.csv")
        target_location = CURATED_HDFS
    except Exception:
        images = read_csv(f"{LOCAL_RAW}/images.csv")
        classes = read_csv(f"{LOCAL_RAW}/classes.csv")
        ndvi = read_csv(f"{LOCAL_RAW}/ndvi_stats.csv")
        spectral = read_csv(f"{LOCAL_RAW}/spectral_data.csv")
        target_location = "/opt/spark/curated/landcover_stats"

    # Cast numeric columns
    from pyspark.sql.functions import col
    ndvi_cast = ndvi.select(*[col(c).cast("double").alias(c) if c in ["ndvi_mean","ndvi_std","ndvi_min","ndvi_max"] else col(c) for c in ndvi.columns])
    spectral_cast = spectral.select(*[col(c).cast("double").alias(c) if c in ["red_mean","green_mean","blue_mean","nir_mean","brightness_mean"] else col(c) for c in spectral.columns])

    df = images.join(classes, "class_id", "left") \
               .join(ndvi_cast, "image_id", "left") \
               .join(spectral_cast, "image_id", "left")

    agg = df.groupBy("class_name").agg(
        avg("ndvi_mean").alias("ndvi_avg"),
        stddev("ndvi_mean").alias("ndvi_stddev"),
        spark_min("ndvi_min").alias("ndvi_global_min"),
        spark_max("ndvi_max").alias("ndvi_global_max"),
        avg("red_mean").alias("red_avg"),
        avg("nir_mean").alias("nir_avg"),
        avg("brightness_mean").alias("brightness_avg"),
        count("image_id").alias("image_count")
    )

    agg.write.mode("overwrite").parquet(target_location)

    spark.sql("""
        CREATE TABLE IF NOT EXISTS landcover_aggregates (
            class_name STRING,
            ndvi_avg DOUBLE,
            ndvi_stddev DOUBLE,
            ndvi_global_min DOUBLE,
            ndvi_global_max DOUBLE,
            red_avg DOUBLE,
            nir_avg DOUBLE,
            brightness_avg DOUBLE,
            image_count BIGINT
        ) USING PARQUET LOCATION '{}'
    """.format(target_location))


if __name__ == "__main__":
    main()
